#!/usr/bin/env bash
# ============================================================
#  广播站点歌系统 一键部署脚本
#  用法（服务器上执行，需 root）：
#    国内：bash -c "$(curl -sSL https://cdn.jsdelivr.net/gh/xihe41017/radio-song@main/deploy/install.sh)"
#    海外：bash -c "$(curl -sSL https://raw.githubusercontent.com/xihe41017/radio-song/main/deploy/install.sh)"
#
#  部署过程中会询问端口；也可用环境变量跳过：
#    PORT=8081 ADMIN_PASSWORD=xxx JWT_SECRET=xxx DOMAIN=xxx bash -c "$(curl ...)"
# ============================================================
set -euo pipefail

# ---------- 颜色 ----------
C_G='\033[0;32m'; C_Y='\033[0;33m'; C_B='\033[0;34m'; C_R='\033[0;31m'; C_0='\033[0m'
info() { echo -e "${C_B}[信息]${C_0} $*"; }
ok()   { echo -e "${C_G}[成功]${C_0} $*"; }
warn() { echo -e "${C_Y}[注意]${C_0} $*"; }
err()  { echo -e "${C_R}[错误]${C_0} $*"; exit 1; }

# ---------- 配置 ----------
GIT_USER="xihe41017"
REPO="radio-song"
APP_DIR="/opt/$REPO"
DEFAULT_PORT="8001"
DOMAIN="${DOMAIN:-_}"

rand() { head -c 48 /dev/urandom | base64 | tr -dc 'a-zA-Z0-9' | head -c "${1:-18}" || true; }
JWT_SECRET="${JWT_SECRET:-$(rand 32)$(rand 32)}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-}"   # 先初始化，避免 set -u 报错

# 交互式设置管理员密码（主 shell 直接读入，兼容 sudo/非交互场景）
ask_password() {
  local name="$1" p1 p2
  [ -n "$ADMIN_PASSWORD" ] && return   # 已用环境变量指定则跳过
  ADMIN_PASSWORD=""
  while :; do
    read -r -s -p "请设置${name}管理员密码（≥6位，直接回车自动生成）: " p1; echo
    if [ -z "$p1" ]; then ADMIN_PASSWORD="$(rand 18)"; return; fi
    read -r -s -p "请再次输入确认: " p2; echo
    if [ "$p1" = "$p2" ] && [ "${#p1}" -ge 6 ]; then ADMIN_PASSWORD="$p1"; return; fi
    warn "两次输入不一致或密码过短（需≥6位），请重试"
  done
}

# ---------- 前置检查 ----------
[ "$(id -u)" -eq 0 ] || err "请用 root 运行：sudo bash -c \"\$(curl ...)\""
if command -v apt-get >/dev/null 2>&1; then PKG=apt
elif command -v yum >/dev/null 2>&1; then PKG=yum
else err "仅支持 Debian/Ubuntu/CentOS/RHEL"; fi
command -v curl >/dev/null 2>&1 || { info "安装 curl..."; $PKG install -y curl >/dev/null 2>&1; }

echo ""
info "============================================"
info "  广播站点歌系统 一键部署"
info "============================================"
echo ""

# ---------- 选择端口 ----------
choose_port() {
  local input="${PORT:-}"
  if [ -z "$input" ]; then
    read -r -p "请输入点歌系统要使用的端口 [默认 $DEFAULT_PORT]: " input
    input="${input:-$DEFAULT_PORT}"
  fi
  case "$input" in ''|*[!0-9]*) err "端口必须是数字";; esac
  [ "$input" -ge 1 ] && [ "$input" -le 65535 ] || err "端口范围 1~65535"
  if command -v ss >/dev/null 2>&1 && ss -ltn 2>/dev/null | grep -q ":$input "; then
    err "端口 $input 已被占用，请换一个"
  fi
  PORT="$input"
}
choose_port
ask_password '点歌系统'
info "部署端口：$PORT"

# ---------- 安装依赖 ----------
info "安装依赖（python3 / node / git）..."
if [ "$PKG" = "apt" ]; then
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq
  apt-get install -y -qq git python3 python3-venv python3-pip >/dev/null
else
  yum install -y -q git python3 python3-pip >/dev/null
fi

if ! command -v node >/dev/null 2>&1 || [ "$(node -v | tr -dc '0-9' | cut -c1-2)" -lt 20 ]; then
  info "安装 Node.js 20 ..."
  if [ "$PKG" = "apt" ]; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - >/dev/null 2>&1
    apt-get install -y -qq nodejs >/dev/null
  else
    curl -fsSL https://rpm.nodesource.com/setup_20.x | bash - >/dev/null 2>&1
    yum install -y -q nodejs >/dev/null
  fi
fi
node -v >/dev/null 2>&1 || err "Node.js 安装失败"

# ---------- 拉取代码 ----------
info "拉取项目代码..."
mkdir -p /opt
cd /opt
[ -d "$REPO" ] || git clone --depth 1 "https://github.com/$GIT_USER/$REPO.git"
cd "$APP_DIR"
git pull --ff-only >/dev/null 2>&1 || true

# ---------- 后端 + 前端 ----------
info "配置后端环境..."
cd "$APP_DIR/backend"
python3 -m venv .venv
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet -r requirements.txt

info "构建前端..."
cd "$APP_DIR/frontend"
npm install --no-audit --no-fund
npm run build

# ---------- 环境配置 ----------
info "写入环境配置..."
mkdir -p /etc/campus
cat > /etc/campus/radio.env <<EOF
ADMIN_PASSWORD=$ADMIN_PASSWORD
JWT_SECRET=$JWT_SECRET
EOF
chmod 600 /etc/campus/radio.env

# ---------- systemd ----------
info "注册 systemd 服务（端口 $PORT，开机自启 + 崩溃重启）..."
cat > /etc/systemd/system/campus-radio.service <<EOF
[Unit]
Description=Campus Radio Song Request
After=network.target
[Service]
WorkingDirectory=$APP_DIR/backend
EnvironmentFile=/etc/campus/radio.env
ExecStart=$APP_DIR/backend/.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
Restart=always
RestartSec=3
[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable campus-radio >/dev/null 2>&1 || true
if ! systemctl restart campus-radio 2>&1; then
  systemctl status campus-radio --no-pager -n 15 2>&1 | tail -20 || true
  err "服务启动失败，请根据上方日志排查（systemctl status campus-radio）"
fi
sleep 3
if ! systemctl is-active --quiet campus-radio; then
  warn "服务未正常运行，错误信息如下："
  systemctl status campus-radio --no-pager -n 15 2>&1 | tail -20 || true
  journalctl -u campus-radio --no-pager -n 20 2>/dev/null | tail -20 || true
  err "请根据上方日志排查（systemctl status campus-radio）"
fi
ok "服务已启动"

# ---------- 自动更新（每分钟 cron 检查，失败不影响当前服务） ----------
setup_autoupdate() {
  local svc="$1" repo="$2" port="$3" name="$4"
  cat > "/usr/local/bin/campus-$name-update.sh" <<'UPDATE_EOF'
#!/usr/bin/env bash
# 自动更新（后台调度 / 手动触发；任何一步失败都保持当前版本，不影响正在运行的服务）
set -uo pipefail
REPO_DIR="__REPO__"
SERVICE="__SERVICE__"
PORT="__PORT__"
LOG="/var/log/campus-__NAME__-update.log"
STATE="/var/log/campus-__NAME__-update.state"   # 供管理后台读取更新状态
exec 9>/tmp/campus-__NAME__-update.lock || exit 0
flock -n 9 2>/dev/null || exit 0   # 避免并发更新
log() { echo "$(date '+%F %T') $*" >> "$LOG"; }
setstate() { echo "$1|$(date +%s)|$2" > "$STATE"; }
cd "$REPO_DIR" || exit 0
# 1. 检查远程是否有新提交（网络失败跳过，不影响当前）
git fetch origin --quiet 2>/dev/null || { setstate fail "git fetch 失败（网络）"; exit 0; }
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)
[ "$LOCAL" = "$REMOTE" ] && exit 0   # 无更新
# 2. 只看是否改动了代码文件；仅文档类更新直接同步
CHANGED=$(git diff --name-only "$LOCAL" "$REMOTE" | grep -E '^(frontend/|backend/)' || true)
if [ -z "$CHANGED" ]; then
  git pull --ff-only --quiet 2>/dev/null && log "文档类更新，已同步代码（无需重启）"
  setstate ok "已同步文档类更新（无需重启）"
  exit 0
fi
log "检测到更新：$LOCAL → $REMOTE"
setstate updating "正在更新"
PREV="$LOCAL"
# 3. 拉取（失败则保持当前）
git pull --ff-only --quiet 2>/dev/null || { setstate fail "git pull 失败，保持当前"; exit 0; }
# 4. 后端依赖（失败则保持当前）
cd "$REPO_DIR/backend"
.venv/bin/pip install --quiet -r requirements.txt 2>/dev/null || { setstate fail "依赖安装失败，保持当前"; exit 0; }
# 5. 前端构建到临时目录（失败则保持当前，旧 dist 仍被服务）
cd "$REPO_DIR/frontend"
npm install --no-audit --no-fund --silent 2>/dev/null || { setstate fail "npm install 失败，保持当前"; exit 0; }
npm run build -- --outDir dist.tmp >/dev/null 2>&1 || { setstate fail "前端构建失败，保持当前"; rm -rf dist.tmp; exit 0; }
rm -rf dist && mv dist.tmp dist
# 6. 重启并健康检查（失败回滚到上一版本）
systemctl restart "$SERVICE" 2>/dev/null || { setstate fail "服务重启失败"; exit 0; }
sleep 3
if ! curl -sf "http://127.0.0.1:$PORT/" >/dev/null 2>&1; then
  log "健康检查失败，回滚到 $PREV"
  git reset --hard "$PREV" >/dev/null 2>&1
  cd "$REPO_DIR/frontend" && npm run build >/dev/null 2>&1
  systemctl restart "$SERVICE" 2>/dev/null || true
  setstate fail "更新后健康检查失败，已回滚"
else
  log "更新完成 → $REMOTE"
  setstate ok "更新完成 → ${REMOTE:0:8}"
fi
UPDATE_EOF
  sed -i "s|__REPO__|$repo|g; s|__SERVICE__|$svc|g; s|__PORT__|$port|g; s|__NAME__|$name|g" "/usr/local/bin/campus-$name-update.sh"
  chmod +x "/usr/local/bin/campus-$name-update.sh"
  # 更新调度由后端负责（后台可设开关/间隔/手动更新），这里只生成更新脚本
  info "已生成更新脚本（后台可配置自动更新规则）"
}

setup_autoupdate "campus-radio" "$APP_DIR" "$PORT" "radio"

# ---------- 可选 Nginx ----------
if command -v nginx >/dev/null 2>&1; then
  read -r -p "是否配置 Nginx：80 端口反向代理到 $PORT ？（y/N）: " ng
  if [ "${ng:-n}" = "y" ] || [ "${ng:-n}" = "Y" ]; then
    info "配置 Nginx ..."
    if [ "$PKG" = "apt" ]; then
      SITE=/etc/nginx/sites-available/radio; ENABLED=/etc/nginx/sites-enabled/radio
    else
      SITE=/etc/nginx/conf.d/radio.conf; ENABLED=/etc/nginx/conf.d/radio.conf
    fi
    cat > "$SITE" <<EOF
server {
    listen 80;
    server_name $DOMAIN;
    location / {
        proxy_pass http://127.0.0.1:$PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Forwarded-For \$remote_addr;
    }
}
EOF
    if [ "$PKG" = "apt" ]; then
      ln -sf "$SITE" "$ENABLED"
    fi
    if nginx -t >/dev/null 2>&1; then
      systemctl reload nginx
      ok "Nginx 配置完成（80 端口 → $PORT）"
    else
      warn "Nginx 配置未通过测试，请手动检查（直接访问端口 $PORT 也可用）"
    fi
  fi
fi

# ---------- 防火墙 ----------
command -v ufw >/dev/null 2>&1 && ufw allow "$PORT"/tcp >/dev/null 2>&1 || true
command -v firewall-cmd >/dev/null 2>&1 && { firewall-cmd --permanent --add-port="$PORT"/tcp >/dev/null 2>&1 || true; firewall-cmd --reload >/dev/null 2>&1 || true; }

# ---------- 结果 ----------
sleep 2
STATUS=$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$PORT/" || true)
LISTEN=$(ss -ltn 2>/dev/null | grep -c ":$PORT " || echo "0")
echo ""
ok "============================================"
ok "  点歌系统部署完成！"
ok "============================================"
echo ""
echo -e "  访问地址：${C_Y}http://服务器IP:$PORT/${C_0}"
[ "${ng:-n}" = "y" ] || [ "${ng:-n}" = "Y" ] && echo -e "  也可以：${C_Y}http://服务器IP/${C_0}"
echo ""
echo -e "  管理员：${C_B}admin${C_0} / ${C_G}$ADMIN_PASSWORD${C_0}"
echo ""
warn "请立即保存上面的密码！"

if [ "$STATUS" != "200" ]; then
  echo ""
  warn "⚠️ 本机访问 $PORT 返回状态 $STATUS（端口监听: $LISTEN），请按下面排查："
  echo "  1. 服务状态：systemctl status campus-radio"
  echo "  2. 服务日志：journalctl -u campus-radio -n 50 --no-pager"
  echo "  3. 云服务器控制台 → 安全组 → 入方向规则：放行 TCP $PORT 端口"
  echo "     （阿里云/腾讯云/华为云的安全组是在系统外拦的，脚本无法自动放行）"
else
  echo ""
  echo "  常用命令："
  echo "    systemctl status campus-radio"
  echo "    systemctl restart campus-radio"
fi
echo ""
