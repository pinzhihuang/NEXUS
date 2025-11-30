#!/bin/bash
# Railway startup script - ensures PORT is properly used

# Use Railway's PORT or default to 8000
PORT=${PORT:-8000}

echo "Starting Gunicorn on port $PORT"

# Start Gunicorn with proper configuration
exec gunicorn app:app \
  --bind "0.0.0.0:${PORT}" \
  --workers 4 \
  --threads 2 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile - \
  --log-level info

