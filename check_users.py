from app import app, db
from models import User
with app.app_context():
    print(f"Total Users: {User.query.count()}")
    print(f"Students: {User.query.filter_by(role='student').count()}")
    print(f"Mentors: {User.query.filter_by(role='mentor').count()}")
    roles = [r[0] for r in db.session.query(User.role).distinct().all()]
    print(f"Distinct Roles: {roles}")
    # Sample user
    u = User.query.first()
    if u:
        print(f"Sample User: {u.name}, Role: {u.role}")
