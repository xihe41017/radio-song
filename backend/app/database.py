from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False, "timeout": 30},
)
with engine.connect() as conn:
    conn.execute(text("PRAGMA journal_mode=WAL"))

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def _ensure_column(conn, table, column, ddl):
    cols = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
    if column not in {c[1] for c in cols}:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {ddl}"))
        print(f"[迁移] 已为 {table} 添加 {column} 列")


def run_migrations():
    with engine.connect() as conn:
        _ensure_column(conn, "admins", "role", "role VARCHAR(20) DEFAULT 'admin'")
        _ensure_column(conn, "admins", "permissions", "permissions VARCHAR(500)")
        _ensure_column(conn, "admins", "created_at", "created_at DATETIME")
        conn.commit()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
