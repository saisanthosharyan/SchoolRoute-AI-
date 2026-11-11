
from app.database.base import Base
from app.database.connection import engine

# Import all models so SQLAlchemy registers their tables.
from app.database import models  # noqa: F401


def initialize_database():
    """Create all registered database tables."""

    Base.metadata.create_all(bind=engine)

    print("DATABASE INITIALIZED SUCCESSFULLY")
    print(f"Total tables: {len(Base.metadata.tables)}")

    for table_name in Base.metadata.tables:
        print(f"  [OK] {table_name}")


if __name__ == "__main__":
    initialize_database()
