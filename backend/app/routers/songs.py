from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app import netease
from app.ratelimit import dyn, limiter

router = APIRouter(prefix="/api/songs", tags=["songs"])


@router.get("/search")
@limiter.limit(dyn("rate_search", "10/minute"))
def search_songs(
    request: Request,
    q: str = Query(..., min_length=1, max_length=50),
    limit: int = Query(10, ge=1, le=20),
):
    try:
        return netease.search_songs(q.strip(), limit)
    except netease.NeteaseError as e:
        raise HTTPException(status_code=502, detail=f"网易云音乐搜索暂时不可用（{e}）")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"网易云音乐搜索暂时不可用（{e}）")
