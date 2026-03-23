
import sys
import os

# Add the current directory to sys.path
sys.path.append(os.getcwd())

try:
    from app.main import app
    print("✅ app.main imported successfully")
except Exception as e:
    import traceback
    traceback.print_exc()
