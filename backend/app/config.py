"""广播站点歌系统 - 全局配置（环境变量可覆盖）。"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent  # backend/


class Settings:
    DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'data' / 'radio.db'}")

    # 独立管理员账号（与表白墙无关，首次启动自动创建）
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

    JWT_SECRET = os.getenv("JWT_SECRET", "radio-station-dev-secret")
    JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "168"))

    CORS_ORIGINS = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")

    # 自动更新（部署脚本生成更新脚本；Windows 开发环境不可用）
    UPDATE_SCRIPT = os.getenv("UPDATE_SCRIPT", "/usr/local/bin/campus-radio-update.sh")
    UPDATE_STATE = os.getenv("UPDATE_STATE", "/var/log/campus-radio-update.state")
    UPDATE_SERVICE = os.getenv("UPDATE_SERVICE", "campus-radio")

    # Nginx 域名解析（后台可配置；Windows 开发环境仅预览）
    NGINX_DOMAINS_FILE = os.getenv("NGINX_DOMAINS_FILE", "/etc/campus/radio-domains.json")
    NGINX_CONF_FILE = os.getenv("NGINX_CONF_FILE", "/etc/nginx/conf.d/campus-radio-domains.conf")


settings = Settings()


# (key, 默认值, 描述)
DEFAULT_SETTINGS = [
    ("site_name", "广播站点歌台", "站点名称", 0),
    ("request_limit", "3", "单个IP最多同时点播(待播放)的歌曲数", 0),
    ("rate_search", "20", "搜索接口限速(次/分钟)", 1),
    ("rate_request", "3", "点歌接口限速(次/分钟)", 1),
    ("rate_login", "10", "管理员登录限速(次/分钟)", 1),
    ("auto_update_enabled", "0", "自动更新开关（仅超管）", 1),
    ("auto_update_interval", "5", "自动更新检查间隔(分钟)（仅超管）", 1),
    ("jwt_secret", settings.JWT_SECRET, "JWT签名密钥（修改后管理员需重新登录）", 1),
    ("neteast_proxy", "", "网易云搜索代理地址(如 http://127.0.0.1:7890，留空直连；服务器被反爬时填)", 1),
]
