#!/bin/sh
set -e

echo "Initializing local SQLite database..."
python init_db.py

echo "Restoring users from Firebase to local database..."
python restore_users.py

echo "Restoring meetings from Firebase to local database..."
python restore_meetings.py

echo "Starting application..."
exec "$@"
