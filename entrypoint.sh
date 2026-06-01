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

exec "$@"
