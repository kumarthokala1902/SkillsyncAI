import sys
import os
from werkzeug.security import generate_password_hash

# Add current directory to path
sys.path.append(os.getcwd())

try:
    from app import app
    from models import db, User
    
    with app.app_context():
        # Check if users already exist to avoid duplicates
        existing_users = {u.name: u for u in User.query.all()}
        
        mentors_to_add = [
            {
                "name": "Siva GK",
                "email": "siva@skillsync.ai",
                "skills": "Python, Machine Learning, Data Science",
                "role": "mentor",
                "is_mentor": True,
                "bio": "Expert in AI and Backend Development."
            },
            {
                "name": "seshu",
                "email": "seshu@skillsync.ai",
                "skills": "Frontend, UI/UX, Design Systems",
                "role": "mentor",
                "is_mentor": True,
                "bio": "FAANG Level Designer and Educator."
            }
        ]
        
        for m_data in mentors_to_add:
            if m_data['name'] not in existing_users:
                print(f"Seeding mentor: {m_data['name']}")
                u = User(
                    name=m_data['name'],
                    email=m_data['email'],
                    password_hash=generate_password_hash('password123', method='pbkdf2:sha256'),
                    skills=m_data['skills'],
                    role=m_data['role'],
                    is_mentor=m_data['is_mentor'],
                    bio=m_data['bio']
                )
                db.session.add(u)
        
        db.session.commit()
        print("Success: Mentor data restoration complete.")
            
except Exception as e:
    print(f"Error seeding data: {e}")
    import traceback
    traceback.print_exc()
