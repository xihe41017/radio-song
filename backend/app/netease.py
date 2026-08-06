"""网易云音乐搜索封装（走公开网页接口，无需登录）。

封面说明：网易云专辑接口有频控，这里对封面做「尽力而为」获取 + 缓存。
拿不到封面时返回空字符串，前端用占位图兜底。
"""
import json
import urllib.parse
import urllib.request

SEARCH_URL = "https://music.163.com/api/search/get/web"
ALBUM_URL = "https://music.163.com/api/album/{album_id}?ext=true"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Referer": "https://music.163.com/",
}

_cover_cache: dict = {}


def _fetch(url: str) -> dict:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


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
    """搜索歌曲，返回列表（封面尽力而为）。"""
    params = urllib.parse.urlencode({"s": query, "type": 1, "limit": limit})
    data = _fetch(f"{SEARCH_URL}?{params}")
    songs = (data.get("result") or {}).get("songs") or []

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

    # 封面尽力而为（命中缓存立即，未命中尝试一次，频控则空）
    for r in results:
        r["cover"] = _cover(r["album_id"])
    return results

