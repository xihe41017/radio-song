from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_perm
from app.models import Admin
from app.permissions import ADMIN_DEFAULT_PERMS, effective_perms, set_perms
from app.schemas import AdminUserCreate, AdminUserOut, AdminUserUpdate
from app.security import hash_password

router = APIRouter(prefix="/api/admin/users", tags=["users"])

# 账号管理仅超管
_admin = Depends(require_perm("users.manage"))


def _out(a: Admin) -> AdminUserOut:
    return AdminUserOut(
        id=a.id, username=a.username, role=a.role,
        permissions=sorted(effective_perms(a)), created_at=a.created_at,
    )


@router.get("", response_model=List[AdminUserOut])
def list_users(_: Admin = _admin, db: Session = Depends(get_db)):
    return [_out(a) for a in db.query(Admin).order_by(Admin.created_at.asc()).all()]


@router.post("", response_model=AdminUserOut, status_code=201)
def create_user(payload: AdminUserCreate, _: Admin = _admin, db: Session = Depends(get_db)):
    if db.query(Admin).filter_by(username=payload.username).first():
        raise HTTPException(status_code=400, detail="用户名已存在")
    a = Admin(
        username=payload.username,
        password_hash=hash_password(payload.password),
        role=payload.role,
    )
    if payload.role == "admin":
        set_perms(a, payload.permissions or ADMIN_DEFAULT_PERMS)
    db.add(a)
    db.commit()
    db.refresh(a)
    return _out(a)


@router.put("/{user_id}", response_model=AdminUserOut)
def update_user(user_id: int, payload: AdminUserUpdate, admin: Admin = _admin, db: Session = Depends(get_db)):
    a = db.get(Admin, user_id)
    if not a:
        raise HTTPException(status_code=404, detail="用户不存在")
    if a.id == admin.id and (payload.role and payload.role != "super_admin"):
        raise HTTPException(status_code=400, detail="不能降低自己的权限")
    if payload.role is not None:
        a.role = payload.role
        if payload.role != "super_admin" and payload.permissions is None:
            set_perms(a, effective_perms(a))
    if payload.permissions is not None:
        set_perms(a, payload.permissions)
    if payload.password:
        a.password_hash = hash_password(payload.password)
    db.commit()
    db.refresh(a)
    return _out(a)


@router.delete("/{user_id}", status_code=204)
def delete_user(user_id: int, admin: Admin = _admin, db: Session = Depends(get_db)):
    a = db.get(Admin, user_id)
    if not a:
        raise HTTPException(status_code=404, detail="用户不存在")
    if a.id == admin.id:
        raise HTTPException(status_code=400, detail="不能删除自己")
    db.delete(a)
    db.commit()
