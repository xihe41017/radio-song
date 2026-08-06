"""管理后台权限体系（与表白墙类似，轻量版）。
超管恒有全部权限；普通管理员 = 角色默认权限 ∪ 额外授予的权限。"""
import json

from app.models import Admin

# (key, 分组, 说明)
PERMISSIONS = [
    ("content.manage", "点歌管理", "标记已播 / 删除点歌"),
    ("settings.view", "系统设置", "查看系统设置"),
    ("settings.site_name", "系统设置", "修改：站点名称"),
    ("settings.request_limit", "系统设置", "修改：单IP点歌数"),
]
PERMISSION_KEYS = [k for k, _g, _d in PERMISSIONS]
PERMISSION_LABELS = {k: (g, d) for k, g, d in PERMISSIONS}

# 管理员默认权限
ADMIN_DEFAULT_PERMS = [
    "content.manage", "settings.view",
    "settings.site_name", "settings.request_limit",
]


def _perm_list(a: Admin) -> list:
    if not a.permissions:
        return []
    try:
        data = json.loads(a.permissions)
        return data if isinstance(data, list) else []
    except (TypeError, ValueError):
        return []


def effective_perms(a: Admin) -> set:
    if a.role == "super_admin":
        return set(PERMISSION_KEYS)
    perms = set(_perm_list(a))
    if not perms and a.role == "admin":
        perms = set(ADMIN_DEFAULT_PERMS)  # 旧数据兼容
    return perms


def has_perm(a: Admin, key: str) -> bool:
    if a.role == "super_admin":
        return True
    return key in effective_perms(a)


def set_perms(a: Admin, keys: list):
    a.permissions = json.dumps(sorted(set(k for k in keys if k in PERMISSION_KEYS)), ensure_ascii=False)
