"""Nginx 域名解析管理：后台可配置将特定域名反向代理到本系统。

- 数据源：JSON 文件（/etc/campus/radio-domains.json），不是解析 Nginx 配置本身
- 每次变更：写配置文件 → nginx -t 校验 → reload
- 自动检测/安装 Nginx（apt/yum/dnf）
- Windows 开发环境：仅返回预览配置，不做任何系统级操作
"""
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

# ---------- 每系统常量（confession 项目需同步修改） ----------
SYSTEM_NAME = "radio"
SERVICE_NAME = "campus-radio"
DEFAULT_PORT = 8001
CLIENT_MAX_BODY = "50m"

# 域名存储文件（后台管理的数据源）
DOMAINS_FILE = os.getenv("NGINX_DOMAINS_FILE", "/etc/campus/radio-domains.json")

# 生成的 Nginx 配置（apt 用 sites-available + 软链，yum 用 conf.d）
CONF_FILE = os.getenv("NGINX_CONF_FILE", "/etc/nginx/conf.d/campus-radio-domains.conf")

_DOMAIN_RE = re.compile(r"^([a-z0-9]([a-z0-9-]*[a-z0-9])?\.)+[a-z0-9][a-z0-9-]*[a-z0-9]$|^localhost$")


def is_server() -> bool:
    return os.name != "nt"


def nginx_installed() -> bool:
    return shutil.which("nginx") is not None


def nginx_active() -> bool:
    if not nginx_installed():
        return False
    try:
        r = subprocess.run(["systemctl", "is-active", "nginx"], capture_output=True, text=True, timeout=10)
        return r.stdout.strip() == "active"
    except Exception:
        return False


def detect_port() -> int:
    """从 systemd 服务文件或环境变量探测本系统监听端口。"""
    env_port = os.getenv("PORT")
    if env_port and env_port.isdigit():
        return int(env_port)
    unit = Path(f"/etc/systemd/system/{SERVICE_NAME}.service")
    if unit.exists():
        try:
            for line in unit.read_text(encoding="utf-8", errors="ignore").splitlines():
                m = re.search(r"--port\s+(\d+)", line)
                if m:
                    return int(m.group(1))
        except OSError:
            pass
    return DEFAULT_PORT


def _load() -> list:
    p = Path(DOMAINS_FILE)
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _save(domains: list):
    p = Path(DOMAINS_FILE)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(domains, ensure_ascii=False, indent=2), encoding="utf-8")


def _render(domains: list, port: int) -> str:
    """根据域名列表生成 Nginx server 块（HTTP；带证书的额外生成 443 块）。"""
    lines = [f"# 由 {SYSTEM_NAME} 管理后台自动生成，请勿手动编辑", f"# 后端端口: {port}", ""]
    plain = [d["domain"] for d in domains if not d.get("ssl_cert")]
    for d in domains:
        if d.get("ssl_cert"):
            # HTTPS 443 块 + HTTP 80 跳转到 HTTPS
            lines.append(f"""server {{
    listen 443 ssl;
    server_name {d['domain']};
    ssl_certificate {d['ssl_cert']};
    ssl_certificate_key {d['ssl_key']};
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    location / {{
        proxy_pass http://127.0.0.1:{port};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
}}
server {{
    listen 80;
    server_name {d['domain']};
    return 301 https://$host$request_uri;
}}""")
    if plain:
        lines.append(f"""server {{
    listen 80;
    server_name {' '.join(plain)};
    client_max_body_size {CLIENT_MAX_BODY};
    location / {{
        proxy_pass http://127.0.0.1:{port};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
}}""")
    return "\n\n".join(lines)


def _write_conf(conf: str) -> str:
    p = Path(CONF_FILE)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(conf, encoding="utf-8")
    # apt 系需要 sites-enabled 软链；conf.d 无需。CONF_FILE 已选 conf.d，直接可用。
    return str(p)


def _nginx_test() -> str:
    r = subprocess.run(["nginx", "-t"], capture_output=True, text=True, timeout=30)
    return (r.stderr or r.stdout or "").strip()


def _reload() -> str:
    r = subprocess.run(["systemctl", "reload", "nginx"], capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        return (r.stderr or r.stdout or "reload 失败").strip()
    return ""


def install_nginx() -> tuple:
    """安装并启动 Nginx。返回 (ok, message)。"""
    if nginx_installed():
        return True, "Nginx 已安装"
    if not is_server():
        return False, "Windows 开发环境无需安装 Nginx"
    pkg = "apt-get" if shutil.which("apt-get") else ("dnf" if shutil.which("dnf") else ("yum" if shutil.which("yum") else None))
    if not pkg:
        return False, "未识别的包管理器（仅支持 apt/yum/dnf）"
    info("安装 Nginx...")
    r = subprocess.run([pkg, "install", "-y", "nginx"], capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        return False, (r.stderr or r.stdout or "安装失败").strip()[-300:]
    subprocess.run(["systemctl", "enable", "--now", "nginx"], capture_output=True, text=True, timeout=60)
    return True, "Nginx 已安装并启动"


def apply(domains: list) -> tuple:
    """写入配置 → nginx -t → reload。返回 (ok, message)。"""
    if not is_server():
        return False, "Windows 开发环境不支持写 Nginx 配置（仅预览）"
    if not nginx_installed():
        return False, "服务器未安装 Nginx，请先安装"
    port = detect_port()
    conf = _render(domains, port)
    _write_conf(conf)
    err = _nginx_test()
    if err and "successful" not in err:
        return False, f"nginx -t 校验失败：{err[-300:]}"
    err = _reload()
    if err:
        return False, f"nginx reload 失败：{err[-300:]}"
    _save(domains)
    return True, "Nginx 配置已更新并重载"


def add_domain(domain: str, ssl_cert: str = "", ssl_key: str = "") -> tuple:
    domain = (domain or "").strip().lower().rstrip(".")
    if not domain:
        return False, "域名不能为空"
    if not _DOMAIN_RE.match(domain):
        return False, "域名格式不正确（示例：radio.example.com）"
    domains = _load()
    if any(d["domain"] == domain for d in domains):
        return False, f"域名 {domain} 已存在"
    entry = {"domain": domain, "ssl_cert": (ssl_cert or "").strip(), "ssl_key": (ssl_key or "").strip()}
    if entry["ssl_cert"] or entry["ssl_key"]:
        if not (entry["ssl_cert"] and entry["ssl_key"]):
            return False, "证书和私钥需同时填写"
        if is_server():
            for f in (entry["ssl_cert"], entry["ssl_key"]):
                if not Path(f).exists():
                    return False, f"证书文件不存在：{f}"
    domains.append(entry)
    return apply(domains)


def remove_domain(domain: str) -> tuple:
    domain = (domain or "").strip().lower()
    domains = [d for d in _load() if d["domain"] != domain]
    if len(domains) == len(_load()):
        return False, f"域名 {domain} 不存在"
    return apply(domains)


def status() -> dict:
    port = detect_port()
    domains = _load()
    return {
        "is_server": is_server(),
        "nginx_installed": nginx_installed(),
        "nginx_active": nginx_active(),
        "port": port,
        "domains_file": DOMAINS_FILE,
        "conf_file": CONF_FILE,
        "domains": domains,
        "preview": _render(domains, port),
    }


def info(msg: str):
    print(f"[信息] {msg}")
