import logging

from app import app, db

logger = logging.getLogger(__name__)

with app.app_context():
    logger.info("Creating database tables if they do not exist")
    db.create_all()
    logger.info("Database schema initialization complete")
