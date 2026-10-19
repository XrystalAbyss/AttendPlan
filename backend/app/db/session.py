"""Database engine, connection pooling, and session factory for AttendPlan."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Generator

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import Base


def get_default_db_path() -> Path:
    """Resolve the default SQLite database path.

    Adheres to the F1 specification: %LOCALAPPDATA%/AttendPlan/attendplan.sqlite3
    Falls back to user home directory if LOCALAPPDATA is undefined.
    """
    env_override = os.environ.get("ATTENDPLAN_DB_PATH")
    if env_override:
        path = Path(env_override)
    else:
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            base_dir = Path(local_app_data) / "AttendPlan"
        else:
            base_dir = Path.home() / ".attendplan"
        path = base_dir / "attendplan.sqlite3"

    # Ensure parent directory exists
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def build_sqlite_url(db_path: Path | str) -> str:
    """Build standard SQLite database URL."""
    p_str = str(db_path).replace("\\", "/")
    if p_str == ":memory:":
        return "sqlite:///:memory:"
    return f"sqlite:///{p_str}"


def create_app_engine(db_url: str | None = None) -> Engine:
    """Create a configured SQLite engine with foreign keys and WAL mode."""
    if db_url is None:
        db_url = build_sqlite_url(get_default_db_path())

    is_memory = ":memory:" in db_url
    engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False} if "sqlite" in db_url else {},
        echo=False,
    )

    # Enable SQLite foreign keys on every connection
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection: Any, connection_record: Any) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        if not is_memory:
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()

    return engine


# Default application-wide engine and sessionmaker
default_engine = create_app_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=default_engine)


def init_db(engine: Engine | None = None) -> None:
    """Create all tables defined in metadata."""
    eng = engine or default_engine
    Base.metadata.create_all(bind=eng)


# Ensure tables exist for default engine
try:
    init_db(default_engine)
except Exception:
    pass


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

