"""自动更新：后台调度 + 手动触发（纯 Python 实现，不依赖外部 shell 脚本）。

更新逻辑直接在本进程内执行：git fetch → 检测更新 → 重建 venv → 装依赖 →
前端构建 → systemctl 重启 → 健康检查（失败回滚）。这样部署一次之后，
后台「立即更新」永远可用，不会再因为部署脚本过期而失效。
任何一步失败都保持当前版本，不影响正在运行的服务。
"""
import os
import re
import subprocess
import threading
import time
import urllib.request
from pathlib import Path

from app.config import settings
from app.settings_service import service as settings_service

_state = {"updating": False, "last_result": "尚未执行过更新", "last_run_at": None}
_lock = threading.Lock()

DEFAULT_PORT = 8001


def _script_path() -> str:
    return getattr(settings, "UPDATE_SCRIPT", "")


def _state_path() -> str:
    return getattr(settings, "UPDATE_STATE", "/var/log/campus-update.state")


def _repo_dir() -> Path:
    # backend/app/auto_update.py -> 仓库根目录
    return Path(__file__).resolve().parent.parent.parent


def _detect_port() -> int:
    env_port = os.getenv("PORT")
    if env_port and env_port.isdigit():
        return int(env_port)
    unit = Path(f"/etc/systemd/system/{getattr(settings, 'UPDATE_SERVICE', 'campus-radio')}.service")
    if unit.exists():
        try:
            for line in unit.read_text(encoding="utf-8", errors="ignore").splitlines():
                m = re.search(r"--port\s+(\d+)", line)
                if m:
                    return int(m.group(1))
        except OSError:
            pass
    return DEFAULT_PORT


def _venv_bin() -> Path:
    return _repo_dir() / "backend" / ".venv" / ("Scripts" if os.name == "nt" else "bin")


def _run(cmd, cwd=None, timeout=300) -> subprocess.CompletedProcess:
    """统一执行子进程：合并 PATH，捕获输出，带超时。"""
    env = dict(os.environ)
    env["PATH"] = os.environ.get("PATH", "") + ":/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, env=env)


def _write_state(updating: bool, result: str):
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


def _ensure_venv(backend: Path) -> tuple:
    """确保 backend/.venv 存在且可用，返回 (python, pip) 路径。"""
    venv_bin = _venv_bin()
    py = venv_bin / ("python.exe" if os.name == "nt" else "python")
    pip = venv_bin / ("pip.exe" if os.name == "nt" else "pip")
    if not py.exists():
        _run(["python3", "-m", "venv", str(backend / ".venv")], timeout=180)
    if not pip.exists():
        _run([str(py), "-m", "ensurepip", "--default-pip"], timeout=180)
    return py, pip


def _run_update_sync() -> str:
    """同步执行一次更新，返回结果描述（供后台显示）。"""
    if os.name == "nt":
        return "Windows 开发环境不支持自动更新"
    repo = _repo_dir()
    backend = repo / "backend"
    frontend = repo / "frontend"
    service = getattr(settings, "UPDATE_SERVICE", "campus-radio")
    port = _detect_port()

    # 1. 拉取远程最新
    r = _run(["git", "-C", str(repo), "fetch", "origin"], timeout=120)
    if r.returncode != 0:
        return f"git fetch 失败（网络问题？）：{(r.stderr or r.stdout).strip()[-200:]}"
    local = _run(["git", "-C", str(repo), "rev-parse", "HEAD"]).stdout.strip()
    remote = _run(["git", "-C", str(repo), "rev-parse", "origin/main"]).stdout.strip()
    if local == remote:
        return "已是最新版本，无需更新"

    # 2. 判断是否只是文档类改动（无 backend/frontend 代码变更则不重启）
    changed = _run(["git", "-C", str(repo), "diff", "--name-only", local, remote]).stdout.splitlines()
    code_changed = any(l.startswith(("frontend/", "backend/")) for l in changed)

    # 3. 更新代码（reset 比 pull 更稳，忽略本地未提交改动；数据/venv/dist 已被 gitignore 保护）
    r = _run(["git", "-C", str(repo), "reset", "--hard", "origin/main"], timeout=120)
    if r.returncode != 0:
        return f"git 更新失败：{(r.stderr or r.stdout).strip()[-200:]}"
    if not code_changed:
        return "已同步文档类更新（无需重启）"

    # 4. 重建/修复 venv 并安装后端依赖
    py, pip = _ensure_venv(backend)
    r = _run([str(pip), "install", "--quiet", "-r", str(backend / "requirements.txt")], timeout=600)
    if r.returncode != 0:
        return f"依赖安装失败（已拉取代码，未重启）：{(r.stderr or r.stdout).strip()[-200:]}"

    # 5. 前端构建
    r = _run(["npm", "install", "--no-audit", "--no-fund"], cwd=str(frontend), timeout=600)
    if r.returncode != 0:
        return f"npm install 失败（已拉取代码，未重启）：{(r.stderr or r.stdout).strip()[-200:]}"
    r = _run(["npm", "run", "build"], cwd=str(frontend), timeout=600)
    if r.returncode != 0:
        return f"前端构建失败（已拉取代码，未重启）：{(r.stderr or r.stdout).strip()[-200:]}"

    # 6. 重启服务并健康检查（失败回滚到上一版本）
    r = _run(["systemctl", "restart", service], timeout=120)
    if r.returncode != 0:
        return f"服务重启失败（已拉取代码，未重启）：{(r.stderr or r.stdout).strip()[-200:]}"
    time.sleep(3)
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=5)
    except Exception:
        _run(["git", "-C", str(repo), "reset", "--hard", local], timeout=120)
        _run(["systemctl", "restart", service], timeout=120)
        return "健康检查失败，已回滚到上一版本"
    return f"更新完成 → {remote[:8]}"


def trigger() -> str:
    """手动/自动触发更新（非阻塞，后台线程执行）。"""
    if _state["updating"]:
        return "正在更新中，请稍候"
    if os.name == "nt":
        _state["last_result"] = "Windows 开发环境不支持自动更新"
        return _state["last_result"]
    with _lock:
        _state["updating"] = True
        _state["last_run_at"] = time.time()
        _state["last_result"] = "已启动更新"
    _write_state(True, "已启动更新")

    def _worker():
        try:
            result = _run_update_sync()
        except Exception as e:
            result = f"更新失败：{e}"
        with _lock:
            _state["updating"] = False
            _state["last_result"] = result
            _state["last_run_at"] = time.time()
        _write_state(False, result)

    threading.Thread(target=_worker, daemon=True).start()
    return "已启动更新"


def _scheduler():
    """后台线程：每 30 秒检查一次开关与间隔。"""
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
