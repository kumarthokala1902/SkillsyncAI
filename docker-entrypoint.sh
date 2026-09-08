#!/bin/sh
set -e

if [ "${DB_AUTO_CREATE:-false}" = "true" ]; then
	echo "Initializing database schema..."
	python init_db.py
fi

echo "Starting SkillSync..."
exec "$@"
