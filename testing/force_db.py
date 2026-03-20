from app.database.session import engine
from app.database.base import Base
from app.model.candidate import Candidate
import sqlalchemy

print("--- Database Force Sync ---")
try:
    # 1. Check Connection
    with engine.connect() as conn:
        print("✅ Connection: Established.")
    
    # 2. Create Tables
    print("Building tables...")
    Base.metadata.create_all(bind=engine)
    
    # 3. Verify
    inspector = sqlalchemy.inspect(engine)
    tables = inspector.get_table_names()
    
    if "candidates" in tables:
        print("✅ Success! Table 'candidates' is now visible in the DB.")
    else:
        print("❌ Error: Table not found in 'public' schema.")
        
except Exception as e:
    print(f"❌ Error during sync: {e}")