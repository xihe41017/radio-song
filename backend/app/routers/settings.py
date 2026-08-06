from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import DEFAULT_SETTINGS
from app.database import get_db
from app.deps import require_perm
from app.models import Admin, Setting
from app.permissions import has_perm
from app.schemas import SettingOut, SettingUpdate
from app.settings_service import service as settings_service

router = APIRouter(prefix="/api/admin/settings", tags=["settings"])


@router.get("", response_model=List[SettingOut])
def list_settings(admin: Admin = Depends(require_perm("settings.view")), db: Session = Depends(get_db)):
    items = []
    for key, _default, desc, sensitive in DEFAULT_SETTINGS:
        s = db.get(Setting, key)
        value = s.value if s else _default
        # 敏感项（限速/JWT密钥）对非超管隐藏真实值
        if sensitive and admin.role != "super_admin":
            value = "••••••"
        items.append(SettingOut(key=key, value=value, description=desc, sensitive=bool(sensitive)))
    return items


@router.put("/{key}", response_model=SettingOut)
def update_setting(
    key: str,
    payload: SettingUpdate,
    admin: Admin = Depends(require_perm("settings.view")),
    db: Session = Depends(get_db),
):
    meta = {k: (d, s) for k, d, desc, s in DEFAULT_SETTINGS}.get(key)
    if not meta:
        raise HTTPException(status_code=404, detail="设置项不存在")
    _default, sensitive = meta
    if sensitive:
        # 限速 / JWT 密钥：仅超管可改
        if admin.role != "super_admin":
            raise HTTPException(status_code=403, detail="该设置仅超管可修改")
    elif not has_perm(admin, f"settings.{key}"):
        raise HTTPException(status_code=403, detail="没有修改该设置项的权限")
    s = settings_service.set(db, key, payload.value.strip())
    if key == "jwt_secret":
        settings_service._cache.pop("jwt_secret", None)
    return SettingOut(
        key=s.key, value=s.value,
        description=next((d for k, _d, d, _s in DEFAULT_SETTINGS if k == key), ""),
        sensitive=sensitive,
    )
