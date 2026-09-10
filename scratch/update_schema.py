import sys
import os
sys.path.append(os.getcwd())
from firebase_config import init_firebase

def update_db():
    if not init_firebase():
        raise RuntimeError("Firebase initialization failed")
    print("Firestore schema is managed by document writes.")

if __name__ == "__main__":
    update_db()
