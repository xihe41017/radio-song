from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_admin, require_perm
from app.models import Admin, SongRequest
from app.permissions import effective_perms
from app.ratelimit import dyn, limiter
from app.schemas import LoginIn, PasswordIn, RequestAdminOut, Token
from app.security import create_token, hash_password, verify_password

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _to_out(r: SongRequest) -> RequestAdminOut:
    return RequestAdminOut(
        id=r.id, netease_id=r.netease_id, song_name=r.song_name, artist=r.artist,
        album=r.album, cover=r.cover, duration=r.duration, nickname=r.nickname,
        status=r.status, created_at=r.created_at, played_at=r.played_at, ip=r.ip,
    )


@router.get("/me", response_model=Token)
def me(admin: Admin = Depends(require_admin)):
    return Token(
        token="",
        username=admin.username,
        role=admin.role,
        permissions=sorted(effective_perms(admin)),
    )


@router.post("/login", response_model=Token)
@limiter.limit(dyn("rate_login", "10/minute"))
async def login(request: Request, payload: LoginIn, db: Session = Depends(get_db)):
    admin = db.query(Admin).filter_by(username=payload.username.strip()).first()
    if not admin or not verify_password(payload.password, admin.password_hash):
        raise HTTPException(status_code=400, detail="用户名或密码错误")
    return Token(
        token=create_token(db, admin.username),
        username=admin.username,
        role=admin.role,
        permissions=sorted(effective_perms(admin)),
    )


@router.get("/requests", response_model=dict)
def list_requests(
    status: Optional[str] = Query(None, pattern="^(pending|played)$"),
    _: Admin = Depends(require_perm("content.manage")),
    db: Session = Depends(get_db),
):
    q = db.query(SongRequest)
    if status == "pending":
        # 待播放：先点的排前面（下一首在最上）
        rows = q.filter_by(status="pending").order_by(SongRequest.created_at.asc()).limit(200).all()
    else:
        if status:
            q = q.filter_by(status=status)
        rows = q.order_by(SongRequest.created_at.desc()).limit(200).all()
    pending = db.query(SongRequest).filter_by(status="pending").count()
    played = db.query(SongRequest).filter_by(status="played").count()
    return {
        "items": [_to_out(r) for r in rows],
        "stats": {"pending": pending, "played": played, "total": pending + played},
    }


@router.post("/requests/{req_id}/played", response_model=RequestAdminOut)
def mark_played(req_id: int, _: Admin = Depends(require_perm("content.manage")), db: Session = Depends(get_db)):
    r = db.get(SongRequest, req_id)
    if not r:
        raise HTTPException(status_code=404, detail="点歌不存在")
    r.status = "played"
    r.played_at = datetime.now()
    db.commit()
    db.refresh(r)
    return _to_out(r)


@router.delete("/requests/{req_id}", status_code=204)
def delete_request(req_id: int, _: Admin = Depends(require_perm("content.manage")), db: Session = Depends(get_db)):
    r = db.get(SongRequest, req_id)
    if not r:
        raise HTTPException(status_code=404, detail="点歌不存在")
    db.delete(r)
    db.commit()


@router.post("/password")
def change_password(
    payload: PasswordIn,
    admin: Admin = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if not verify_password(payload.old_password, admin.password_hash):
        raise HTTPException(status_code=400, detail="原密码不正确")
    admin.password_hash = hash_password(payload.new_password)
    db.commit()
    return {"ok": True}
