<div align="center">

# 📻 广播站点歌系统

**把你想听的歌，点给广播站** · 校园广播站在线点歌

![Vue 3](https://img.shields.io/badge/Vue%203-4FC08D?style=for-the-badge&logo=vuedotjs&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-646CFF?style=for-the-badge&logo=vite&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white)
![网易云音乐](https://img.shields.io/badge/%E7%BD%91%E6%98%93%E4%BA%91%E9%9F%B3%E4%B9%90-C20D0D?style=for-the-badge)
![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)

接入网易云音乐搜索的校园广播站点歌系统：听众搜歌点歌，广播站后台管理播放。

</div>

---

## ✨ 功能亮点

### 🎧 听众端
| 功能 | 说明 |
| --- | --- |
| 🔍 网易云搜索 | 接入网易云音乐搜索接口，展示歌名/歌手/专辑/封面/时长 |
| 🎵 点歌弹窗 | 点击歌曲弹出确认弹窗（可填昵称，支持匿名） |
| 📃 待播队列 + 已播历史 | 首页实时展示排队歌曲与最近播放记录 |
| 🛡️ 单 IP 防刷 | 同一 IP 最多同时点 3 首，播完释放名额（后台可调） |
| 👑 管理员不限 | 登录管理员点歌无上限 |

### ⚙️ 广播站管理端（`/admin`）
| 功能 | 说明 |
| --- | --- |
| 🎵 点歌管理 | 待播放 / 已播放 / 全部三视图，一键标记已播、删除 |
| ⚙️ 系统设置 | 修改站点名、**单 IP 点歌数**、各接口限速（仅超管） |
| 👥 账号管理 | **新建管理员**、改角色、按权限单独授予/收回（仅超管） |
| 🔑 修改密码 | 独立管理员账号体系，与其它项目无关 |

## 🧱 技术栈

| 层 | 技术 |
| --- | --- |
| 前端 | Vue 3 · Vite（暗色电台主题 · 转盘/均衡器动效） |
| 后端 | Python · FastAPI |
| 数据库 | SQLite |
| 音乐数据 | 网易云音乐公开搜索接口 |
| 安全 | JWT · 权限体系 · IP 防刷 |

## 🚀 快速开始

需要 Python 3.10+ 和 Node.js 18+。

```bash
# 1. 启动后端
cd backend
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt
.venv/Scripts/python run.py          # http://localhost:8001

# 2. 启动前端（开发模式）
cd frontend
npm install
npm run dev                          # http://localhost:5173
```

> 默认管理员：`admin / admin123`，首次启动自动创建，**上线前务必修改**！

### 生产运行（单进程）

```bash
cd frontend && npm run build
cd ../backend && .venv/Scripts/python run.py   # http://localhost:8001
```

## ⚡ 服务器一键部署（Linux）

> 只需一条命令，在 Linux 服务器上（需 root）完成部署。支持 Ubuntu / Debian / CentOS。

```bash
# 国内服务器（jsdelivr CDN 加速，推荐）
bash -c "$(curl -sSL https://cdn.jsdelivr.net/gh/xihe41017/radio-song@main/deploy/install.sh)"

# 海外服务器
bash -c "$(curl -sSL https://raw.githubusercontent.com/xihe41017/radio-song/main/deploy/install.sh)"
```

### 🎛️ 部署过程（交互式）

运行后会依次询问，也可用环境变量跳过：

```
请输入点歌系统要使用的端口 [默认 8001]:   ← 选端口
请设置点歌系统管理员密码（≥6位，直接回车自动生成）: *****   ← 静默输入
请再次输入确认: *****
是否配置 Nginx：80 端口反向代理到 8001？（y/N）:   ← 可选
```

| 设置项 | 说明 |
| --- | --- |
| 端口 | 任意 1~65535，自动检测占用（默认 8001） |
| 管理员密码 | 静默输入 + 二次确认，留空自动生成强随机密码 |
| JWT 密钥 | 自动生成（可用 `JWT_SECRET` 指定） |
| Nginx | 可选，80 端口反代到你选的端口 |

**非交互部署**：

```bash
PORT=8081 ADMIN_PASSWORD='强密码' JWT_SECRET='随机串' bash -c "$(curl -sSL https://cdn.jsdelivr.net/gh/xihe41017/radio-song@main/deploy/install.sh)"
```

### 📦 脚本自动完成

```
安装依赖(Python/Node) → 拉取代码 → 后端venv → 前端构建
→ 写入管理员密码/JWT密钥 → 注册systemd服务(开机自启+崩溃重启)
→ 可选Nginx反代 → 输出访问地址和密码
```

### 🔄 自动更新管理（后台可配置）

部署后自带自动更新能力，**超管登录后台 → 系统设置 → 自动更新** 即可管理：

- **开关**：启用后按设定间隔自动检查更新
- **间隔**：每分钟 ~ 每天，自定义
- **手动更新**：一键立即更新
- **安全**：更新失败不影响当前运行；构建到临时目录、失败自动回滚

部署完成后访问 `http://服务器IP:端口/`，管理员密码在脚本输出末尾，请立即保存。

## 📖 手动部署

```bash
cd radio-song/backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
ADMIN_PASSWORD='强密码' JWT_SECRET='随机长字符串' nohup .venv/bin/python run.py > server.log 2>&1 &

# Nginx 反代（必须设置 X-Forwarded-For，否则单 IP 防刷失效）
server {
    listen 80;
    server_name 你的域名;
    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

### ⚠️ 关于网易云搜索与封面
- 使用网易云公开网页接口，受其频控影响，搜索偶尔会提示「稍后再试」
- 专辑封面接口有频控，采用「尽力获取 + 缓存」策略，拿不到时用 🎵 占位图兜底

## 📜 开源许可

本项目基于 [MIT License](LICENSE) 开源，欢迎学习、使用与二次开发。
