from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import netease
from app.database import get_db
from app.deps import get_ip, optional_admin
from app.models import Admin, SongRequest
from app.schemas import QuotaOut, RequestCreate, RequestOut
from app.settings_service import service as settings_service

router = APIRouter(prefix="/api", tags=["requests"])


def _to_out(r: SongRequest) -> RequestOut:
    return RequestOut(
        id=r.id, netease_id=r.netease_id, song_name=r.song_name, artist=r.artist,
        album=r.album, cover=r.cover, duration=r.duration, nickname=r.nickname,
        status=r.status, created_at=r.created_at, played_at=r.played_at,
    )


@router.post("/requests", response_model=RequestOut, status_code=201)
def create_request(
    request: Request,
    payload: RequestCreate,
    db: Session = Depends(get_db),
    admin: Admin | None = Depends(optional_admin),
):
    ip = get_ip(request)
    limit = settings_service.get_int(db, "request_limit", 3)

    # 单个 IP 最多同时点 limit 首待播放；登录管理员不受此限制
    if not admin:
        pending = (
            db.query(SongRequest)
            .filter_by(ip=ip, status="pending")
            .count()
        )
        if pending >= limit:
            raise HTTPException(
                status_code=429,
                detail=f"单个 IP 最多同时点 {limit} 首，等播完再点吧～",
            )

    # 去重：同一首歌已在待播列表
    dup = db.query(SongRequest).filter_by(netease_id=payload.netease_id, status="pending").first()
    if dup:
        raise HTTPException(status_code=400, detail="这首歌已经在点歌列表里啦")

    # 封面尽力而为：客户端没带封面时，后端补一次（带缓存与节流）
    cover = (payload.cover or "").strip()
    if not cover and payload.album_id:
        cover = netease._cover(payload.album_id)

    r = SongRequest(
        netease_id=payload.netease_id,
        song_name=payload.song_name,
        artist=(payload.artist or "").strip(),
        album=(payload.album or "").strip(),
        cover=cover,
        duration=payload.duration or 0,
        nickname=payload.nickname,
        ip=ip,
        status="pending",
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return _to_out(r)


@router.get("/requests/queue", response_model=dict)
def queue(db: Session = Depends(get_db)):
    """公开：待播队列 + 最近已播。"""
    pending = (
        db.query(SongRequest)
        .filter_by(status="pending")
        .order_by(SongRequest.created_at.asc())
        .all()
    )
    played = (
        db.query(SongRequest)
        .filter_by(status="played")
        .order_by(SongRequest.played_at.desc())
        .limit(30)
        .all()
    )
    return {
        "pending": [_to_out(r) for r in pending],
        "played": [_to_out(r) for r in played],
    }


@router.get("/requests/quota", response_model=QuotaOut)
def my_quota(
    request: Request,
    db: Session = Depends(get_db),
    admin: Admin | None = Depends(optional_admin),
):
    """当前 IP 还能点几首；登录管理员不限。"""
    ip = get_ip(request)
    limit = settings_service.get_int(db, "request_limit", 3)
    if admin:
        return QuotaOut(remaining=999, limit=limit)
    pending = db.query(SongRequest).filter_by(ip=ip, status="pending").count()
    return QuotaOut(remaining=max(0, limit - pending), limit=limit)
