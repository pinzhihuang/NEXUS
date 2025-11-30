#!/bin/bash
# Railway startup script

set -e

echo "=== Railway Startup ==="
echo "PORT: ${PORT:-8080}"
echo "PUPPETEER_EXECUTABLE_PATH: ${PUPPETEER_EXECUTABLE_PATH:-not set}"

# Try to find and set Chromium path
if command -v chromium &> /dev/null; then
    export PUPPETEER_EXECUTABLE_PATH=$(which chromium)
    echo "Found Chromium: $PUPPETEER_EXECUTABLE_PATH"
    $PUPPETEER_EXECUTABLE_PATH --version || echo "Chromium version check failed"
else
    echo "WARNING: Chromium not found in PATH"
fi

echo "======================="

# Start Gunicorn
exec gunicorn app:app \
  --bind "0.0.0.0:${PORT:-8080}" \
  --workers 2 \
  --threads 2 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile - \
  --log-level info \
  --preload


