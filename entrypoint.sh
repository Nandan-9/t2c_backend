#!/bin/sh
set -e

# Wait for Postgres to accept connections
echo "Waiting for PostgreSQL..."
until uv run python -c "
import os, psycopg2
psycopg2.connect(
    dbname=os.environ['DB_NAME'],
    user=os.environ['DB_USER'],
    password=os.environ['DB_PASSWORD'],
    host=os.environ['DB_HOST'],
    port=os.environ.get('DB_PORT', '5432'),
)
" 2>/dev/null; do
  sleep 1
done
echo "PostgreSQL is ready."

uv run python manage.py migrate --noinput

# Create superuser if credentials are provided and the user doesn't already exist
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
  uv run python manage.py createsuperuser \
    --noinput \
    --username "$DJANGO_SUPERUSER_USERNAME" \
    --email "${DJANGO_SUPERUSER_EMAIL:-admin@example.com}" \
    2>/dev/null || true
fi

exec "$@"
