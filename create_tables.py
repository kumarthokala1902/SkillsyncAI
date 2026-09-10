from firebase_config import init_firebase

if not init_firebase():
    raise RuntimeError("Firebase initialization failed")
print("Firebase services initialized successfully")
