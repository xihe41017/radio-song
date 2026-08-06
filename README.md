# 📻 广播站点歌系统

面向校园广播站的在线点歌系统：听众搜索网易云音乐点歌，广播站管理员在后台标记播放状态。

- **前端**：Vue 3 + Vite（暗色电台主题、发光动效、移动端适配）
- **后端**：Python FastAPI + SQLite（网易云搜索、IP 防刷、独立管理员）
- **网易云音乐**：走公开网页搜索接口，无需登录

## 功能

### 听众端
| 功能 | 说明 |
| --- | --- |
| 搜索点歌 | 接入网易云音乐搜索，**点击歌曲弹出确认弹窗**（填昵称点歌） |
| 匿名点歌 | 无需注册，昵称可不填（显示「匿名听众」） |
| 待播队列 | 首页显示排队中的歌曲（第一首高亮「下一首」） |
| 已播历史 | 首页展示最近播放过的歌曲 |
| 防刷限制 | **单个 IP 最多同时点 3 首**（待播放），播完释放名额，可后台调整；**登录管理员不限** |
| 成功提示 | 点歌成功后弹窗显示「已加入待播队列」 |

### 管理端（`/admin`，独立账号体系）
- **点歌管理**：待播放 / 已播放 / 全部 三视图，显示点歌人 IP，标记已播放、删除
- **系统设置**：修改站点名称、**单个 IP 点歌数**（限速/JWT密钥仅超管）
- **账号管理**（仅超管）：**新建管理员**、改角色、单独授予/收回每个用户的权限（仿表白墙权限体系）、重置密码、删除
- 修改自己的密码

> 管理入口统一走 `/admin`，页面不显示管理按钮。

## 目录结构

```
radio-song/
├── backend/
│   ├── app/
│   │   ├── main.py          # 入口（含生产静态托管）
│   │   ├── netease.py       # 网易云搜索 + 封面（尽力而为+缓存）
│   │   ├── models.py        # SongRequest / Admin / Setting
│   │   ├── routers/         # songs / requests / admin
│   │   └── ...
│   ├── data/radio.db
│   ├── requirements.txt
│   └── run.py               # 端口 8001
└── frontend/                # Vue 3
    ├── src/views/           # Home / Request / Admin
    └── vite.config.js       # 代理 /api → 8001
```

## 本地运行

```bash
# 后端（终端 1）
cd backend
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt
.venv/Scripts/python run.py        # http://localhost:8001

# 前端（终端 2）
cd frontend
npm install
npm run dev                        # http://localhost:5173
```

## 生产运行（单进程）

```bash
cd frontend && npm run build
cd ../backend && .venv/Scripts/python run.py   # http://localhost:8001
```

后端检测到 `frontend/dist/` 后自动托管前端，单个进程即可运行。

## 部署到服务器

```bash
# 服务器需 Python 3.10+
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
ADMIN_PASSWORD='强密码' nohup .venv/bin/python run.py > server.log 2>&1 &

# Nginx 反代
server {
    listen 80;
    server_name 你的域名;
    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $remote_addr;   # 关键：IP 防刷识别
    }
}
```

> **注意**：`X-Forwarded-For` 必须设置，否则所有点歌都算作 127.0.0.1，单 IP 3 首限制会立刻触发。

## 说明
- **网易云搜索**：使用公开网页接口，可能受网易频控影响；搜索失败会提示「稍后再试」。
- **封面**：网易云专辑接口有频控，封面「尽力而为」获取并缓存；拿不到时前端用 🎵 占位图兜底。
- **管理员**：默认 `admin / admin123`，登录后请在管理端立即修改密码。
- 环境变量：`ADMIN_USERNAME` / `ADMIN_PASSWORD` / `JWT_SECRET` / `CORS_ORIGINS`。
