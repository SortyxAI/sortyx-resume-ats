# create_tables.py
from app.database.session import engine, Base
from app.model.job import Job  # Import your models so Base knows about them
from app.model.candidate import Candidate # Add your candidate model too

print("🚀 Creating tables in PostgreSQL...")
Base.metadata.create_all(bind=engine)
print("✅ Done! Your 'jobs' and 'candidates' tables are now live.")