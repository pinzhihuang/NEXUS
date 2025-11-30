#!/bin/bash
# Railway startup script - ensures PORT is properly used

# Debug: Show all environment variables related to PORT
echo "=== Environment Check ==="
echo "PORT variable: '${PORT}'"
echo "All environment variables:"
env | grep -i port || echo "No PORT-related variables found"
echo "========================="

# Use Railway's PORT or default to 8080 (Railway's expected port)
PORT=${PORT:-8080}

echo "Starting Gunicorn on port $PORT"
echo "Binding to: 0.0.0.0:${PORT}"

# Start Gunicorn with proper configuration
exec gunicorn app:app \
  --bind "0.0.0.0:${PORT}" \
  --workers 2 \
  --threads 2 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile - \
  --log-level info \
  --preload


