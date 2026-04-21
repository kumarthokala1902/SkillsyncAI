import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

try:
    from app import app
    from models import db, User
    with app.app_context():
        mentors = User.query.filter_by(is_mentor=True).all()
        print(f"Total Mentors: {len(mentors)}")
        for m in mentors:
            print(f"ID: {m.id}, Name: {m.name}, Skills: {m.skills}")
            
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
