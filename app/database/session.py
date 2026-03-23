import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# 1. Load the file
load_dotenv()

# 2. Get the URL
# Use DATABASE_URL from env, which Render provides automatically
DATABASE_URL = os.getenv("DATABASE_URL")

# 3. Validation
if not DATABASE_URL:
    # Fallback for local development if .env is missing or DATABASE_URL is not set
    DATABASE_URL = "postgresql://postgres:Nick%40444@localhost:5432/resumedb"
    print(f"⚠️ DATABASE_URL not found in environment. Using local fallback.")

# 4. Fix prefix for SQLAlchemy (common for Heroku/Render)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# 5. Connect
# If on Render, we might need sslmode=require for some hosted DBs, 
# but usually Render's Internal URL works directly.
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()