import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

# Load DATABASE_URL from environment with fallback to host mapping
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://radar:radar@localhost:5433/dark_content_radar"
)

# Initialize SQLAlchemy engine
engine = create_engine(DATABASE_URL)

# Configure local session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Declare base metadata model
Base = declarative_base()

def get_db():
    """
    FastAPI dependency yielding a database session and closing it after transaction completes.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
