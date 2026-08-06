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

## 📖 部署到服务器

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
