from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import auto_update
from app.database import get_db
from app.deps import require_super_admin
from app.models import Admin
from app.schemas import AutoUpdateIn, AutoUpdateOut
from app.settings_service import service as settings_service

router = APIRouter(prefix="/api/admin/auto-update", tags=["auto-update"])


@router.get("", response_model=AutoUpdateOut)
def get_auto_update(_: Admin = Depends(require_super_admin), db: Session = Depends(get_db)):
    st = auto_update.status()
    return AutoUpdateOut(
        enabled=settings_service.get_bool(db, "auto_update_enabled", False),
        interval=settings_service.get_int(db, "auto_update_interval", 5),
        **st,
    )


@router.put("", response_model=AutoUpdateOut)
def set_auto_update(
    payload: AutoUpdateIn,
    _: Admin = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    settings_service.set(db, "auto_update_enabled", "1" if payload.enabled else "0")
    settings_service.set(db, "auto_update_interval", str(max(1, payload.interval)))
    st = auto_update.status()
    return AutoUpdateOut(enabled=payload.enabled, interval=max(1, payload.interval), **st)


@router.post("/run", response_model=AutoUpdateOut)
def run_auto_update(_: Admin = Depends(require_super_admin), db: Session = Depends(get_db)):
    msg = auto_update.trigger()
    st = auto_update.status()
    st["last_result"] = msg or st["last_result"]
    return AutoUpdateOut(
        enabled=settings_service.get_bool(db, "auto_update_enabled", False),
        interval=settings_service.get_int(db, "auto_update_interval", 5),
        **st,
    )
