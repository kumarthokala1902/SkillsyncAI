from app import db, User, app
import firebase_service as fs_svc
from firebase_config import db_firestore

with app.app_context():
    fs = fs_svc._get_fs()
    if fs:
        users_ref = fs.collection('users')
        docs = users_ref.stream()
        restored = 0
        for doc in docs:
            data = doc.to_dict()
            email = data.get('email')
            if not email:
                continue
            
            existing = User.query.filter_by(email=email).first()
            if not existing:
                print(f"Restoring {email}...")
                user = User(
                    email=email,
                    name=data.get('name', 'Restored User'),
                    role=data.get('role', 'student'),
                    skills=data.get('skills', 'No skills listed'),
                    bio=data.get('bio', ''),
                    college_name=data.get('collegeName', ''),
                    college_code=data.get('collegeCode', '')
                )
                user.set_password('RestoredPassword123!') # Temp password, Firebase Auth is the real auth
                db.session.add(user)
                restored += 1
                
        db.session.commit()
        print(f"Restored {restored} users to local DB.")
    else:
        print("Firebase not configured.")
