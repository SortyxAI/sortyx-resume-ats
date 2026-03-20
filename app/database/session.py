from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 🚨 UPDATE THIS with your actual PostgreSQL credentials
# Format: postgresql://USER:PASSWORD@localhost:PORT/DATABASE_NAME
SQLALCHEMY_DATABASE_URL = "postgresql://postgres:Nick%40444@localhost:5432/resumedb"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# This is the 'Base' that Job and Candidate need to inherit from
Base = declarative_base()

# Dependency to get a DB session for your routes
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()