import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# 1. Load the file
load_dotenv()

# 2. Get the URL
DATABASE_URL = os.getenv("DATABASE_URL")

# 3. Validation
if not DATABASE_URL:
    # This message tells you EXACTLY where it's failing
    raise ValueError(f"❌ DATABASE_URL not found! I am looking in: {os.getcwd()}")

# 4. Fix prefix for SQLAlchemy
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# 5. Connect
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()