#!/bin/bash
# Railway startup script with detailed logging

set -e

echo "========================================="
echo "RAILWAY STARTUP DEBUG"
echo "========================================="
echo "Timestamp: $(date)"
echo "Working directory: $(pwd)"
echo "User: $(whoami)"
echo ""
echo "Environment variables:"
echo "  PORT: ${PORT:-NOT SET}"
echo "  PYTHONPATH: ${PYTHONPATH:-NOT SET}"
echo "  PUPPETEER_EXECUTABLE_PATH: ${PUPPETEER_EXECUTABLE_PATH:-NOT SET}"
echo ""

# Check if app.py exists
if [ -f "app.py" ]; then
    echo "✅ app.py found"
else
    echo "❌ ERROR: app.py NOT FOUND"
    ls -la
    exit 1
fi

# Check if gunicorn is available
if command -v gunicorn &> /dev/null; then
    echo "✅ gunicorn found: $(which gunicorn)"
    gunicorn --version
else
    echo "❌ ERROR: gunicorn NOT FOUND"
    exit 1
fi

# Try to find and set Chromium path
echo ""
echo "Searching for Chromium..."
if command -v chromium &> /dev/null; then
    CHROMIUM_PATH=$(which chromium)
    export PUPPETEER_EXECUTABLE_PATH="$CHROMIUM_PATH"
    echo "✅ Found Chromium: $CHROMIUM_PATH"
    
    # Test Chromium
    if $CHROMIUM_PATH --version &> /dev/null; then
        VERSION=$($CHROMIUM_PATH --version)
        echo "✅ Chromium works: $VERSION"
    else
        echo "⚠️  WARNING: Chromium found but --version failed"
    fi
else
    echo "❌ WARNING: Chromium not found in PATH"
    echo "PATH: $PATH"
fi

echo ""
echo "Final environment:"
echo "  PUPPETEER_EXECUTABLE_PATH: ${PUPPETEER_EXECUTABLE_PATH:-NOT SET}"
echo ""
echo "========================================="
echo "Starting Gunicorn on 0.0.0.0:${PORT:-8080}"
echo "========================================="

# Start Gunicorn with verbose logging
exec gunicorn app:app \
  --bind "0.0.0.0:${PORT:-8080}" \
  --workers 2 \
  --threads 2 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile - \
  --log-level debug \
  --preload 2>&1


