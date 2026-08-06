"""运行时设置服务（带缓存，后台可改）。"""
from sqlalchemy.orm import Session

from app.config import DEFAULT_SETTINGS
from app.models import Admin  # noqa: F401 仅加载模块
from app.database import Base, engine  # noqa: F401


class SettingsService:
    def __init__(self):
        self._cache = {}

    def warm(self, db: Session):
        for k, _d, _desc, _s in DEFAULT_SETTINGS:
            self._cache.setdefault(k, _d)

    def get(self, db: Session, key: str, default: str = None) -> str:
        from app.models import Setting
        if key in self._cache:
            return self._cache[key]
        s = db.get(Setting, key)
        value = s.value if s else default
        self._cache[key] = value
        return "" if value is None else str(value)

    def get_int(self, db: Session, key: str, default: int = 0) -> int:
        try:
            return int(float(self.get(db, key, str(default))))
        except (TypeError, ValueError):
            return default

    def get_bool(self, db: Session, key: str, default: bool = False) -> bool:
        return self.get(db, key, "1" if default else "0") in ("1", "true", "True", "yes")

    def get_cached(self, key: str, default: str = None) -> str:
        value = self._cache.get(key)
        return default if value is None else str(value)

    def set(self, db: Session, key: str, value: str):
        from app.models import Setting
        s = db.get(Setting, key)
        if s is None:
            s = Setting(key=key)
            db.add(s)
        s.value = str(value)
        db.commit()
        db.refresh(s)
        self._cache[key] = str(value)
        return s


service = SettingsService()
