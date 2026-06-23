"""
Database engine + session management.
SQLite by default (DATABASE_URL in .env), swappable for Postgres
by changing DATABASE_URL — SQLAlchemy handles the rest.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from config import settings
from database.models import Base

connect_args = {"check_same_thread": False} if "sqlite" in settings.database_url else {}

engine = create_engine(settings.database_url, connect_args=connect_args, echo=False)
# expire_on_commit=False: this codebase's standard pattern is
#     with get_db_session() as db:
#         rows = db.query(Model).all()
#     # ...then read rows[i].some_column further down, after the session
#     # (and its `with` block) has already closed.
# With the default expire_on_commit=True, SQLAlchemy marks every loaded
# attribute "expired" on commit, so the *next* attribute access tries to
# lazily reload from the session -- which just closed, raising
# DetachedInstanceError. expire_on_commit=False keeps already-loaded
# attributes cached on the Python object instead, so they remain usable
# after the session closes. This does not serve stale data across
# requests: each `with get_db_session()` block still opens a brand new
# session and queries the database fresh every time.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)


def init_db():
    """Create all tables. Safe to call repeatedly (no-op if they exist).

    The on-disk directory only needs to exist for SQLite (the file has to
    live somewhere); for any other backend (Postgres, MySQL, ...) there's
    no local file path to create, so attempting to derive one from the
    connection URL would just create a garbage directory literally named
    after the connection string.
    """
    if settings.database_url.startswith("sqlite"):
        db_file = settings.database_url.replace("sqlite:///", "", 1)
        if db_file and db_file != ":memory:":
            Path(db_file).resolve().parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)


@contextmanager
def get_db_session():
    """Context-managed session for scripts / agents (non-FastAPI usage)."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_db():
    """FastAPI dependency-injection style generator."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
