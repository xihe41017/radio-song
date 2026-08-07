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
    except urllib.error.HTTPError as e:
        raise NeteaseError(f"HTTP {e.code}（可能被网易云反爬拦截）") from e
    except urllib.error.URLError as e:
        reason = getattr(e, "reason", e)
        raise NeteaseError(f"网络错误：{reason}") from e
    try:
        data = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise NeteaseError(f"响应解析失败：{e}") from e
    if not isinstance(data, dict):
        # 反爬时常返回 JSON 字符串或数组，不是对象
        raise NeteaseError(f"响应格式异常（期望 JSON 对象，实际为 {type(data).__name__}）")
    return data


def _cover(album_id) -> str:
    """尽力获取封面：带缓存。接口频控时可能拿不到，返回空。"""
    if not album_id:
        return ""
    if album_id in _cover_cache:
        return _cover_cache[album_id]
    try:
        data = _fetch(ALBUM_URL.format(album_id=album_id))
        album = data.get("album")
        url = album.get("picUrl", "") if isinstance(album, dict) else ""
    except Exception:
        url = ""
    _cover_cache[album_id] = url
    return url


def _parse_song(s) -> dict:
    """解析单首歌，结构异常时返回 None（该条跳过）。"""
    if not isinstance(s, dict):
        return None
    album = s.get("album")
    album = album if isinstance(album, dict) else {}
    artists = s.get("artists")
    artists = artists if isinstance(artists, list) else []
    try:
        return {
            "id": int(s["id"]),
            "name": str(s["name"] or ""),
            "artist": ", ".join(str(a.get("name", "")) for a in artists if isinstance(a, dict)),
            "album": str(album.get("name", "")),
            "album_id": album.get("id"),
            "duration": int((s.get("duration") or 0) / 1000),
        }
    except (KeyError, TypeError, ValueError):
        return None


def _query_tokens(query: str) -> list:
    """把查询词拆成可匹配的片段：中文按单个字符，英文按单词（>1 字符）。"""
    import re as _re
    tokens = []
    for seg in _re.split(r"[\s,，.、]+", query.strip()):
        if not seg:
            continue
        # 含中文的段按 2 字以上滑窗拆，避免单字误匹配
        if _re.search(r"[一-鿿]", seg):
            if len(seg) <= 4:
                tokens.append(seg)
            else:
                for i in range(len(seg) - 1):
                    tokens.append(seg[i : i + 2])
        else:
            if len(seg) > 1:
                tokens.append(seg.lower())
            tokens.append(seg.lower())
    # 去重，保留长度优先
    return sorted(set(tokens), key=len, reverse=True)


def _song_text(song: dict) -> str:
    return f"{song['name']} {song['artist']} {song['album']}".lower()


def _is_relevant(song: dict, tokens: list) -> bool:
    """判断歌曲是否与关键词相关：歌名/歌手/专辑任一处包含任一 token。"""
    if not tokens:
        return True
    text = _song_text(song)
    return any(t in text for t in tokens)


def search_songs(query: str, limit: int = 10) -> list:
    """搜索歌曲，返回与关键词相关的歌曲列表。失败抛 NeteaseError（含原因）。"""
    params = urllib.parse.urlencode({"s": query, "type": 1, "limit": limit})
    tokens = _query_tokens(query)
    last_err = ""
    for base in SEARCH_URLS:
        try:
            data = _fetch(f"{base}?{params}")
            if not isinstance(data, dict):
                last_err = f"{base} 响应格式异常"
                continue
            result = data.get("result")
            songs = result.get("songs") if isinstance(result, dict) else None
            if not songs or not isinstance(songs, list):
                last_err = f"{base} 返回空结果"
                continue
            results = [s for s in (_parse_song(x) for x in songs[:limit]) if s is not None]
            if not results:
                last_err = f"{base} 无有效歌曲"
                continue
            # 风控降级时接口会返回与关键词无关的热门推荐，这里过滤掉
            relevant = [r for r in results if _is_relevant(r, tokens)]
            if not relevant:
                last_err = f"{base} 返回结果与关键词无关（疑似被风控，返回热门推荐）"
                continue
            # 若接口混入无关结果，优先保留相关项；相关项不足时用过滤后的
            results = relevant
            for r in results:
                r["cover"] = _cover(r["album_id"])
            return results
        except NeteaseError as e:
            last_err = str(e)
            continue
        except Exception as e:  # 单接口内部异常不中断轮换
            last_err = f"{base} {e}"
            continue
    raise NeteaseError(last_err or "所有搜索接口均不可用")
