#!/bin/sh
set -e

echo "Waiting for PostgreSQL..."
python manage.py migrate --noinput

exec "$@"
