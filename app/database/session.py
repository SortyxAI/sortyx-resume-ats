import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 1. Pull the URL from the Render Dashboard
DATABASE_URL = os.getenv("DATABASE_URL")

# 2. If it's empty, the app will show a clear error in the logs instead of trying localhost
if not DATABASE_URL:
    raise ValueError("FATAL: DATABASE_URL not found! Check Render Environment tab.")

# 3. Handle the 'postgres://' vs 'postgresql://' fix automatically
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# 4. Create the engine
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()