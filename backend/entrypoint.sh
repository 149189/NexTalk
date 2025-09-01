#!/bin/sh
set -e

# Wait for Redis (optional) if nc available
if command -v nc >/dev/null 2>&1 && [ -n "${REDIS_HOST:-}" ]; then
  host=${REDIS_HOST:-redis}
  port=${REDIS_PORT:-6379}
  i=0
  until nc -z "$host" "$port" >/dev/null 2>&1 || [ $i -ge 20 ]; do
    i=$((i+1))
    echo "Waiting for $host:$port ($i/20)..."
    sleep 1
  done
fi

echo "Applying migrations (if any)..."
python manage.py migrate --noinput || true

# Development server (change to Gunicorn in production)
if [ "$DJANGO_ENV" = "production" ]; then
  echo "Starting gunicorn..."
  exec gunicorn backend.wsgi:application --bind 0.0.0.0:8000 --workers 3
else
  echo "Starting Django dev server..."
  exec python manage.py runserver 0.0.0.0:8000
fi
