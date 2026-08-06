"""公共依赖：IP 识别、管理员鉴权、权限校验。"""
from typing import Optional

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Admin
from app.permissions import has_perm
from app.security import decode_token


def get_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _resolve_admin(db: Session, authorization: Optional[str]) -> Admin | None:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    payload = decode_token(db, authorization.split(" ", 1)[1].strip())
    if not payload or payload.get("role") != "admin":
        return None
    return db.query(Admin).filter_by(username=payload["sub"]).first()


def optional_admin(
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None),
) -> Admin | None:
    """解析当前管理员（未登录返回 None，不报错）。"""
    return _resolve_admin(db, authorization)


def require_admin(
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None),
) -> Admin:
    admin = _resolve_admin(db, authorization)
    if not admin:
        raise HTTPException(status_code=401, detail="请先登录")
    return admin


def require_perm(key: str):
    """按权限键校验（超管恒有全部权限）。"""
    def dep(admin: Admin = Depends(require_admin)) -> Admin:
        if not has_perm(admin, key):
            raise HTTPException(status_code=403, detail="没有该操作权限")
        return admin
    return dep
