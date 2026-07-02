from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.core.config import get_settings

settings = get_settings()

# Engine manages the database connection pool.
engine = create_engine(settings.database_url)

# SessionLocal creates one database session per request.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# All SQLAlchemy models inherit from Base so their metadata can be discovered.
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    # FastAPI dependency that opens a session for the request and always closes it.
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
