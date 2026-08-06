from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


def _force_utc(v: datetime) -> datetime:
    if v.tzinfo is None:
        return v.replace(tzinfo=timezone.utc)
    return v


class RequestCreate(BaseModel):
    netease_id: int
    song_name: str = Field(..., max_length=200)
    artist: Optional[str] = Field(None, max_length=200)
    album: Optional[str] = Field(None, max_length=200)
    album_id: Optional[int] = Field(None)
    cover: Optional[str] = Field(None, max_length=500)
    duration: Optional[int] = Field(0, ge=0, le=3600)
    nickname: Optional[str] = Field(None, max_length=50)

    @field_validator("nickname")
    @classmethod
    def _strip(cls, v):
        if v is None:
            return None
        v = v.strip()
        return v or None


class RequestOut(BaseModel):
    id: int
    netease_id: int
    song_name: str
    artist: str
    album: str
    cover: str
    duration: int
    nickname: Optional[str]
    status: str
    created_at: datetime
    played_at: Optional[datetime] = None
    _utc = field_validator("created_at")(classmethod(lambda cls, v: _force_utc(v)))
    _utc2 = field_validator("played_at")(classmethod(lambda cls, v: _force_utc(v) if v else v))


class RequestAdminOut(RequestOut):
    ip: Optional[str] = None


class QueueOut(BaseModel):
    pending: List[RequestOut]
    played: List[RequestOut]


class LoginIn(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    token: str
    username: str
    role: str = "admin"
    permissions: List[str] = []


class PasswordIn(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=6, max_length=64)


class AdminUserOut(BaseModel):
    id: int
    username: str
    role: str
    permissions: List[str] = []
    created_at: Optional[datetime] = None
    _utc = field_validator("created_at")(classmethod(lambda cls, v: _force_utc(v) if v else v))


class AdminUserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=30, pattern="^[a-zA-Z0-9_]+$")
    password: str = Field(..., min_length=6, max_length=64)
    role: str = Field("admin", pattern="^(admin|super_admin)$")
    permissions: List[str] = []


class AdminUserUpdate(BaseModel):
    role: Optional[str] = Field(None, pattern="^(admin|super_admin)$")
    password: Optional[str] = Field(None, min_length=6, max_length=64)
    permissions: Optional[List[str]] = None


class SettingOut(BaseModel):
    key: str
    value: str
    description: str = ""
    sensitive: bool = False


class SettingUpdate(BaseModel):
    value: str = Field(..., max_length=500)


class AutoUpdateIn(BaseModel):
    enabled: bool = False
    interval: int = Field(5, ge=1, le=1440)


class AutoUpdateOut(BaseModel):
    enabled: bool = False
    interval: int = 5
    script_exists: bool = False
    updating: bool = False
    last_result: str = ""
    last_run_at: Optional[float] = None


class QuotaOut(BaseModel):
    remaining: int   # 该 IP 还能点几首
    limit: int
