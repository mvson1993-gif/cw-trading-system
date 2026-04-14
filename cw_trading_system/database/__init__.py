# cw_trading_system/database/__init__.py

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
import os

# Base for all ORM models
Base = declarative_base()

# Database URL - will be configured from settings
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./cw_trading.db"
)

# Engine (lazy initialization in production)
engine = None
SessionLocal = None

def init_db(database_url: str = DATABASE_URL):
    """Initialize database engine and session factory."""
    global engine, SessionLocal
    engine = create_engine(
        database_url,
        echo=os.getenv("DB_ECHO", "false").lower() == "true",
        connect_args={"check_same_thread": False} if "sqlite" in database_url else {}
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return engine

def get_session():
    """Get a new database session."""
    if SessionLocal is None:
        init_db()
    return SessionLocal()

def create_all():
    """Create all tables."""
    if engine is None:
        init_db()
    Base.metadata.create_all(bind=engine)

def drop_all():
    """Drop all tables (use with caution)."""
    if engine is None:
        init_db()
    Base.metadata.drop_all(bind=engine)

__all__ = ['Base', 'init_db', 'get_session', 'create_all', 'drop_all', 'DATABASE_URL']
