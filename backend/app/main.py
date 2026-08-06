from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import DEFAULT_SETTINGS, settings
from app.database import Base, SessionLocal, engine, run_migrations
from app.models import Admin, Setting  # noqa: F401 确保建表前已加载
from app.ratelimit import limiter
from app.routers import admin, requests, settings as settings_router, songs, users
from app.security import hash_password
from app.settings_service import service as settings_service

DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
HAS_DIST = (DIST / "index.html").exists()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    run_migrations()
    db = SessionLocal()
    for key, default, desc, sensitive in DEFAULT_SETTINGS:
        if db.get(Setting, key) is None:
            db.add(Setting(key=key, value=str(default), description=desc, sensitive=sensitive))
    if not db.query(Admin).first():
        db.add(Admin(
            username=settings.ADMIN_USERNAME,
            password_hash=hash_password(settings.ADMIN_PASSWORD),
            role="super_admin",
        ))
        print(f"[提示] 已创建超级管理员：{settings.ADMIN_USERNAME} / {settings.ADMIN_PASSWORD}")
    elif not db.query(Admin).filter_by(role="super_admin").first():
        # 老库迁移：保证至少有一个超管
        first = db.query(Admin).order_by(Admin.id.asc()).first()
        first.role = "super_admin"
        print(f"[提示] 已将 {first.username} 提升为超级管理员")
    db.commit()
    settings_service.warm(db)
    db.close()
    yield


app = FastAPI(title="广播站点歌系统 API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(songs.router)
app.include_router(requests.router)
app.include_router(admin.router)
app.include_router(settings_router.router)
app.include_router(users.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


if HAS_DIST:
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        if full_path.startswith("api/"):
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        target = DIST / full_path
        if full_path and target.is_file():
            return FileResponse(target)
        return FileResponse(DIST / "index.html")

    print("[提示] 已启用前端静态托管模式")
