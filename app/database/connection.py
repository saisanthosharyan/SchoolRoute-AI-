
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.config import PROJECT_ROOT, settings


def create_database_engine(database_url):
    """Create a database engine with SQLite foreign keys enabled."""

    engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False}
        if database_url.startswith("sqlite")
        else {},
        pool_pre_ping=True,
    )

    if database_url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def enable_sqlite_foreign_keys(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


# Existing starter database. Do not change its behavior.
engine = create_database_engine(settings.DATABASE_URL)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


# Separate full-scale database.
FULL_DATABASE_PATH = PROJECT_ROOT / "schoolroute_full.db"
FULL_DATABASE_URL = f"sqlite:///{FULL_DATABASE_PATH.as_posix()}"

full_engine = create_database_engine(FULL_DATABASE_URL)

FullSessionLocal = sessionmaker(
    bind=full_engine,
    autoflush=False,
    autocommit=False,
)


def get_db():
    """Provide the starter database session."""

    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


def get_full_db():
    """Provide the full-scale database session."""

    db = FullSessionLocal()

    try:
        yield db
    finally:
        db.close()
