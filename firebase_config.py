"""
firebase_config.py
──────────────────
Initialises Firebase Admin SDK (Firestore + Auth) from environment variables.
Exports:
  - db_firestore  : Firestore client  (or None if service account not configured)
  - fb_auth       : Firebase Auth     (or None if service account not configured)
  - firebase_enabled : bool flag

Never import raw credentials here – everything comes from os.environ via .env
"""
import os
import json
import logging

logger = logging.getLogger(__name__)

# ── Lazy-load firebase_admin so the app still starts even if the package
#    is missing or the service account file hasn't been placed yet. ──────────

db_firestore = None
fb_auth = None
firebase_enabled = False


def init_firebase():
    """
    Call once at application startup (inside an app context is fine).
    Returns True if Firebase was successfully initialised, False otherwise.
    """
    global db_firestore, fb_auth, firebase_enabled

    # Already initialised?
    if firebase_enabled:
        return True

    try:
        import firebase_admin
        from firebase_admin import credentials, firestore, auth

        service_account_path = os.environ.get("FIREBASE_SERVICE_ACCOUNT_KEY", "/app/service-account.json")

        # Support both a file path AND an inline JSON string (useful for
        # container / cloud environments where secrets are injected as env vars)
        if service_account_path.strip().startswith("{"):
            cred_data = json.loads(service_account_path)
            cred = credentials.Certificate(cred_data)
        elif os.path.isfile(service_account_path):
            cred = credentials.Certificate(service_account_path)
        else:
            logger.error(
                "Firebase service account not found at '%s'. "
                "Firestore sync is REQUIRED. Set FIREBASE_SERVICE_ACCOUNT_KEY to enable it.",
                service_account_path,
            )
            raise ValueError(f"Missing Firebase credentials at {service_account_path}")

        # Avoid double-initialisation if multiple calls happen
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)

        db_firestore = firestore.client()
        fb_auth = auth
        firebase_enabled = True
        logger.info("✅ Firebase Admin SDK initialised – Firestore sync ENABLED")
        return True

    except ImportError as exc:
        logger.error(
            "firebase-admin package not installed. Run: pip install firebase-admin. "
            "Firestore sync is REQUIRED."
        )
        raise RuntimeError("firebase-admin package is missing") from exc
    except Exception as exc:
        logger.error("Firebase initialisation failed: %s", exc)
        raise RuntimeError(f"Firebase initialisation failed: {exc}") from exc


# ── Client-side config (safe to expose to the browser JS) ──────────────────
def get_client_config() -> dict:
    """Returns Firebase JS SDK config from environment variables."""
    return {
        "apiKey":            os.environ.get("FIREBASE_API_KEY", ""),
        "authDomain":        os.environ.get("FIREBASE_AUTH_DOMAIN", ""),
        "projectId":         os.environ.get("FIREBASE_PROJECT_ID", ""),
        "storageBucket":     os.environ.get("FIREBASE_STORAGE_BUCKET", ""),
        "messagingSenderId": os.environ.get("FIREBASE_MESSAGING_SENDER_ID", ""),
        "appId":             os.environ.get("FIREBASE_APP_ID", ""),
        "measurementId":     os.environ.get("FIREBASE_MEASUREMENT_ID", ""),
    }
