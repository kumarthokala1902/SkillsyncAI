import logging

from firebase_config import init_firebase

logger = logging.getLogger(__name__)

logger.info("Initializing Firebase services")
if not init_firebase():
    raise RuntimeError("Firebase initialization failed")
logger.info("Firebase initialization complete")
