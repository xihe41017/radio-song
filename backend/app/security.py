import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone

import jwt

from app.config import settings

_ALGO = "HS256"
_ITER = 100_000


def hash_password(password: str, salt: str | None = None) -> str:
    if salt is None:
        salt = os.urandom(16).hex()
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), _ITER)
    return f"{salt}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, _ = stored.split("$", 1)
    except ValueError:
        return False
    return hmac.compare_digest(hash_password(password, salt), stored)


def create_token(db, username: str) -> str:
    from app.settings_service import service as settings_service
    secret = settings_service.get(db, "jwt_secret", settings.JWT_SECRET) or settings.JWT_SECRET
    payload = {
        "sub": username,
        "role": "admin",
        "exp": datetime.now(timezone.utc) + timedelta(hours=settings.JWT_EXPIRE_HOURS),
    }
    return jwt.encode(payload, secret, algorithm=_ALGO)


def decode_token(db, token: str) -> dict | None:
    from app.settings_service import service as settings_service
    secret = settings_service.get(db, "jwt_secret", settings.JWT_SECRET) or settings.JWT_SECRET
    try:
        return jwt.decode(token, secret, algorithms=[_ALGO])
    except jwt.PyJWTError:
        return None
