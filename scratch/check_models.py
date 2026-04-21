import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

try:
    from app import app
    from models import db
    from sqlalchemy.orm import configure_mappers
    
    with app.app_context():
        # This will trigger deep mapper initialization and catch relationship conflicts
        print("Configuring SQLAlchemy mappers...")
        configure_mappers()
        print("Success: SQLAlchemy mappers initialized correctly and relationships verified.")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
