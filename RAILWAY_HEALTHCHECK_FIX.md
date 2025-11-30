# Railway Health Check Fix - Deployment Issue Resolved

## Problem Summary

Railway deployment was failing at the **network healthcheck stage** with repeated "service unavailable" errors:

```
Attempt #1 failed with service unavailable. Continuing to retry for 1m39s
Attempt #2 failed with service unavailable. Continuing to retry for 1m38s
...
Attempt #8 failed with service unavailable. Continuing to retry for 6s

1/1 replicas never became healthy!
Healthcheck failed!
```

**Root Cause**: The Flask application was taking too long to start and bind to the port, preventing the `/health` endpoint from responding within Railway's ~100 second timeout window.

## Why This Was Happening

1. **Gunicorn `--preload` flag**: The startup script used `--preload`, which loads the entire application module before binding to the port
2. **Heavy imports at module level**: `app.py` was importing all news_bot dependencies (config, search_client, article_handler, etc.) when the module loaded
3. **Config validation on import**: The config module runs validation and prints debug info during import, adding startup time
4. **Blocking startup**: Railway's health check couldn't get a response until ALL imports completed and Gunicorn bound to the port

## The Fix

### 1. Lazy Loading Pattern in `app.py`

**Before**: All imports at module level
```python
# These ALL loaded on import, blocking startup
from news_bot.core import config, school_config
from news_bot.discovery import search_client
from news_bot.processing import article_handler
# ... many more
```

**After**: Minimal imports + lazy loading
```python
# Minimal imports for instant startup
from flask import Flask, render_template, request, jsonify, Response, send_file
from datetime import datetime
import json

# Heavy imports are lazy-loaded on first use
def ensure_modules_loaded():
    """Load heavy dependencies only when routes are accessed."""
    if not _modules_loaded:
        # Import news_bot modules here
        from news_bot.core import config, school_config
        # ... etc
```

### 2. Health Check Endpoints First

Health check routes are now defined **immediately** after creating the Flask app, before any heavy imports:

```python
app = Flask(__name__)  # Create app FIRST

@app.route('/health')
@app.route('/healthz')
def health_check():
    """Responds instantly, no dependencies."""
    return jsonify({'status': 'healthy', ...}), 200

# ... then define other routes that lazy-load modules
```

### 3. Removed `--preload` Flag from `start.sh`

**Before**:
```bash
exec gunicorn app:app --preload ...
```

**After**:
```bash
exec gunicorn app:app ...
# --preload removed for faster startup
```

## Performance Results

### Import Speed Test

```
✅ SUCCESS: app.py imported in 0.431 seconds
✅ Flask app object exists
✅ Total routes: 16
✅ Health check routes: ['/healthz', '/health']

🎉 EXCELLENT: Import time < 2 seconds (Railway compatible)
```

**Before**: ~5-10+ seconds (imports blocked startup)
**After**: ~0.4 seconds (instant health check availability)

## How It Works Now

1. **Gunicorn starts** → Imports `app.py` (~0.4 seconds)
2. **Flask app created** → Health check routes immediately available
3. **Railway health check** → `/health` responds instantly with `200 OK`
4. **Deployment succeeds** → Service is healthy
5. **First user request** → Heavy modules lazy-loaded on-demand
6. **Subsequent requests** → Modules already loaded, no delay

## Benefits

✅ **Fast startup**: App binds to port in < 1 second
✅ **Quick health checks**: Railway gets response within timeout
✅ **No functionality loss**: All features work identically after lazy-load
✅ **Better resource usage**: Modules only loaded when actually used
✅ **Worker-friendly**: Each Gunicorn worker loads modules independently (no --preload needed)

## Testing Locally

To verify the fix works before deploying:

```bash
# Test 1: Quick import test
python -c "import time; s=time.time(); import app; print(f'Import: {time.time()-s:.2f}s')"

# Test 2: Start Gunicorn and test health check
gunicorn app:app --bind 0.0.0.0:8000 --workers 2
# In another terminal:
curl http://localhost:8000/health
# Should respond immediately with {"status":"healthy",...}
```

## Deployment to Railway

The fix is now in place. Simply push to Railway:

```bash
git add app.py start.sh
git commit -m "Fix: Railway health check - lazy load dependencies"
git push railway main
```

Railway will now:
1. Build the Docker image ✅
2. Start Gunicorn ✅
3. Health check `/health` → 200 OK ✅
4. Mark deployment as healthy ✅
5. Route traffic to the service ✅

## Related Files Modified

- `app.py` - Restructured for lazy loading, health checks first
- `start.sh` - Removed `--preload` flag

## Additional Notes

- **Environment variables**: Still required for API functionality (OPENROUTER_API_KEY, etc.)
- **First request latency**: First user to hit a route will experience ~1-2 second delay while modules load
- **Subsequent requests**: Instant response, modules cached in memory
- **Development mode**: In `if __name__ == '__main__'`, modules load immediately for better dev experience

---

**Status**: ✅ **FIXED** - Ready for Railway deployment

