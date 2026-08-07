"""自动更新：后台调度 + 手动触发。
超管可在后台设置开关与间隔；实际更新动作由部署脚本生成的 update 脚本执行。
任何一步失败都会保持当前版本，不影响正在运行的服务（详见部署脚本）。
"""
import os
import subprocess
import threading
import time

from app.config import settings
from app.settings_service import service as settings_service

_state = {"updating": False, "last_result": "尚未执行过更新", "last_run_at": None}
_lock = threading.Lock()


def _script_path() -> str:
    return getattr(settings, "UPDATE_SCRIPT", "")


def _state_path() -> str:
    return getattr(settings, "UPDATE_STATE", "/var/log/campus-update.state")


def _write_state(updating: bool, result: str):
    """同步写入状态文件（与更新脚本写入同一路径，前端 status() 读取）。"""
    try:
        st = _read_state()
        last_run_at = st["last_run_at"] or time.time()
        if not updating:
            last_run_at = time.time()
        with open(_state_path(), "w", encoding="utf-8") as f:
            f.write(f"{'updating' if updating else 'ok'}|{last_run_at}|{result}")
    except Exception:
        pass


def _read_state() -> dict:
    try:
        with open(_state_path(), encoding="utf-8") as f:
            parts = f.read().strip().split("|", 2)
        return {
            "updating": parts[0] == "updating",
            "last_result": parts[2] if len(parts) > 2 else "",
            "last_run_at": float(parts[1]) if len(parts) > 1 and parts[1] else None,
        }
    except Exception:
        return {"updating": False, "last_result": "尚未执行过更新", "last_run_at": None}


def status() -> dict:
    st = _read_state()
    # 以内存态为准（刚点击时脚本尚未写文件），否则回退文件态
    if _state["updating"]:
        st = {"updating": True, "last_result": _state["last_result"], "last_run_at": _state["last_run_at"]}
    elif _state["last_result"] and not st["last_run_at"]:
        st = {"updating": False, "last_result": _state["last_result"], "last_run_at": _state["last_run_at"]}
    return {
        "script_exists": bool(_script_path()) and os.path.exists(_script_path()),
        "updating": st["updating"],
        "last_result": st["last_result"],
        "last_run_at": st["last_run_at"],
    }


def trigger() -> str:
    if _state["updating"]:
        return "正在更新中，请稍候"
    path = _script_path()
    if not path or not os.path.exists(path):
        _state["last_result"] = "未找到更新脚本（仅服务器部署环境可用）"
        return _state["last_result"]
    if os.name == "nt":
        _state["last_result"] = "Windows 开发环境不支持自动更新"
        return _state["last_result"]
    with _lock:
        _state["updating"] = True
        _state["last_run_at"] = time.time()
        _state["last_result"] = "已启动更新"
    _write_state(True, "已启动更新")
    try:
        log = _state_path().replace(".state", ".log")
        subprocess.Popen(f"setsid nohup {path} >> {log} 2>&1 &", shell=True)
        return "已启动更新"
    except Exception as e:
        with _lock:
            _state["updating"] = False
        _state["last_result"] = f"启动失败：{e}"
        _write_state(False, f"启动失败：{e}")
        return _state["last_result"]


def _scheduler():
    while True:
        time.sleep(30)
        try:
            from app.database import SessionLocal

            db = SessionLocal()
            enabled = settings_service.get_bool(db, "auto_update_enabled", False)
            interval = settings_service.get_int(db, "auto_update_interval", 5)
            db.close()
        except Exception:
            continue
        if enabled and interval > 0:
            last = _state["last_run_at"]
            if last is None or time.time() - last >= interval * 60:
                trigger()


def start_scheduler():
    threading.Thread(target=_scheduler, daemon=True).start()
