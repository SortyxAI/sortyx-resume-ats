from app.database.session import engine
from app.database.base import Base
from app.model.candidate import Candidate # Ensure this is imported!

print("Connecting to database...")
try:
    Base.metadata.create_all(bind=engine)
    print("✅ Success! Tables created in PostgreSQL.")
except Exception as e:
    print(f"❌ Failed to create tables: {e}")