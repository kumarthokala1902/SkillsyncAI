from app import app, db

with app.app_context():
    print("Creating DB tables manually...")
    db.create_all()
    print("Done!")
