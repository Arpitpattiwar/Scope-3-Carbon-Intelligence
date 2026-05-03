from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings


def get_database_url() -> str:
    database_url = settings.DATABASE_URL.strip()
    localhost_markers = ("@localhost", "@127.0.0.1", "@::1")

    if settings.is_render and any(marker in database_url for marker in localhost_markers):
        raise RuntimeError(
            "DATABASE_URL is not configured for Render. "
            "Set DATABASE_URL on the Render backend service to your Render Postgres "
            "Internal Database URL, or deploy with render.yaml so fromDatabase injects it."
        )

    return database_url


engine = create_engine(get_database_url(), pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
