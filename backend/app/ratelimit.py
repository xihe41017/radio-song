from slowapi import Limiter
from starlette.requests import Request

from app.settings_service import service as settings_service


def _rate_key(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def dyn(key: str, default: str):
    def _limiter():
        v = str(settings_service.get_cached(key, default) or default).strip()
        # 只存数字（如 20），自动补单位；兼容旧的 "20/minute" 格式
        if v.isdigit():
            return f"{v}/minute"
        return v
    return _limiter


limiter = Limiter(key_func=_rate_key, default_limits=["1000/minute"])
