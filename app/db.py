"""Database engine, declarative base and request-scoped session provider."""
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    """Single declarative base shared by all ORM models."""


def build_engine(url: str):
    """SQLite needs check_same_thread disabled for the in-memory test database."""
    if url.startswith("sqlite"):
        return create_engine(url, connect_args={"check_same_thread": False})
    return create_engine(url, pool_pre_ping=True)


engine = build_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: one SQLAlchemy session per request, always closed."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
