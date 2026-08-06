from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from app.database import Base


class SongRequest(Base):
    """一条点歌请求。status: pending(待播放) / played(已播放)"""
    __tablename__ = "requests"

    id = Column(Integer, primary_key=True, index=True)
    netease_id = Column(Integer, index=True)      # 网易云歌曲 ID
    song_name = Column(String(200))
    artist = Column(String(200), default="")
    album = Column(String(200), default="")
    cover = Column(String(500), default="")       # 封面 URL
    duration = Column(Integer, default=0)         # 秒
    nickname = Column(String(50), nullable=True)  # 可匿名，留空显示「匿名听众」
    ip = Column(String(45), index=True)           # 点歌 IP（防刷/溯源）
    status = Column(String(20), default="pending", index=True)
    created_at = Column(DateTime, default=datetime.now, index=True)
    played_at = Column(DateTime, nullable=True)


class Admin(Base):
    """广播站管理员。role: super_admin(超管) / admin(普通管理员)
    permissions: JSON 数组，超管额外授予的权限键（超管恒有全部权限）。"""
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, index=True)
    password_hash = Column(String(128))
    role = Column(String(20), default="admin")
    permissions = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.now)


class Setting(Base):
    __tablename__ = "settings"

    key = Column(String(50), primary_key=True)
    value = Column(String(500), default="")
    description = Column(String(200), default="")
    sensitive = Column(Integer, default=0)
