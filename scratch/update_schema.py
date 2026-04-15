import sys
import os
sys.path.append(os.getcwd())
from app import app, db
from sqlalchemy import text

def update_db():
    with app.app_context():
        # Add columns to Meetup
        try:
            db.session.execute(text("ALTER TABLE meetup ADD COLUMN max_participants INTEGER DEFAULT 50"))
            db.session.execute(text("ALTER TABLE meetup ADD COLUMN banner_url VARCHAR(500)"))
            db.session.commit()
            print("Meetup table updated successfully.")
        except Exception as e:
            print(f"Meetup columns might already exist or error: {e}")
        
        # Create new tables (like Group)
        db.create_all()
        print("db.create_all() executed.")

if __name__ == "__main__":
    update_db()
