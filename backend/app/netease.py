"""网易云音乐搜索封装（走公开网页接口，无需登录）。

- 多接口轮换：网易云有多个公开搜索端点，一个被限/被墙自动换下一个
- 浏览器伪装：带完整 UA + Cookie，降低被反爬拦截概率
- 代理支持：后台可配置 NETEAST_PROXY，服务器被反爬时可走代理出口
- 封面尽力而为 + 缓存：拿不到封面返回空串，前端占位图兜底
- 失败原因透传：搜索失败时返回可诊断的摘要（状态码/网络原因）
"""
import json
import os
import urllib.error
import urllib.parse
import urllib.request

# 可轮换的搜索接口（按优先级；前两个返回结构相同）
SEARCH_URLS = [
    "https://music.163.com/api/search/get/web",
    "https://music.163.com/api/search/get",
    "https://interface.music.163.com/api/search/get/web",
]
ALBUM_URL = "https://music.163.com/api/album/{album_id}?ext=true"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Referer": "https://music.163.com/",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Cookie": "os=pc; osver=Microsoft-Windows-10; appver=8.9.0; NMTID=00O1X9jYd1oQvz7kKpL3q2sT8uV6wX4;",
}

_cover_cache: dict = {}


class NeteaseError(Exception):
    """网易云接口失败，message 为可诊断的摘要。"""


def _proxy() -> str:
    """返回配置的代理地址：优先后台设置项 neteast_proxy，其次环境变量，空则直连。"""
    try:
        from app.settings_service import service as _ss
        val = _ss.get_cached("neteast_proxy") or ""
        if val:
            return str(val).strip()
    except Exception:
        pass
    return (os.getenv("NETEAST_PROXY") or "").strip()


def _fetch(url: str) -> dict:
    req = urllib.request.Request(url, headers=HEADERS)
    proxy = _proxy()
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({"http": proxy, "https": proxy})) if proxy else urllib.request.build_opener()
    try:
        with opener.open(req, timeout=20) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return json.loads(body)
    except urllib.error.HTTPError as e:
        raise NeteaseError(f"HTTP {e.code}（可能被网易云反爬拦截）") from e
    except urllib.error.URLError as e:
        reason = getattr(e, "reason", e)
        raise NeteaseError(f"网络错误：{reason}") from e
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise NeteaseError(f"响应解析失败：{e}") from e


def _cover(album_id) -> str:
    """尽力获取封面：带缓存。接口频控时可能拿不到，返回空。"""
    if not album_id:
        return ""
    if album_id in _cover_cache:
        return _cover_cache[album_id]
    try:
        data = _fetch(ALBUM_URL.format(album_id=album_id))
        url = (data.get("album") or {}).get("picUrl", "")
    except Exception:
        url = ""
    _cover_cache[album_id] = url
    return url


def search_songs(query: str, limit: int = 10) -> list:
    """搜索歌曲，返回列表（封面尽力而为）。失败抛 NeteaseError（含原因）。"""
    params = urllib.parse.urlencode({"s": query, "type": 1, "limit": limit})
    last_err = ""
    for base in SEARCH_URLS:
        try:
            data = _fetch(f"{base}?{params}")
            songs = (data.get("result") or {}).get("songs") or []
            if not songs:
                last_err = f"{base} 返回空结果"
                continue
            results = []
            for s in songs[:limit]:
                album = s.get("album") or {}
                results.append({
                    "id": s["id"],
                    "name": s["name"],
                    "artist": ", ".join(a.get("name", "") for a in s.get("artists", []) or []),
                    "album": album.get("name", ""),
                    "album_id": album.get("id"),
                    "duration": int((s.get("duration") or 0) / 1000),
                })
            for r in results:
                r["cover"] = _cover(r["album_id"])
            return results
        except NeteaseError as e:
            last_err = str(e)
            continue
    raise NeteaseError(last_err or "所有搜索接口均不可用")
