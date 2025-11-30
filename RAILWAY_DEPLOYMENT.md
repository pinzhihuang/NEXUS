# Railway Deployment Guide

## Overview
This app uses Puppeteer/Pyppeteer to generate WeChat-style images from news articles. This requires Chromium to be installed in the Railway environment.

## Configuration Files

### 1. `nixpacks.toml` (Required)
This file tells Railway/Nixpacks to install Chromium and its dependencies:

```toml
[phases.setup]
nixPkgs = ["python311", "chromium"]

[phases.install]
cmds = ["pip install -r requirements.txt"]

[phases.build]
cmds = ["echo 'Build phase complete'"]

[start]
cmd = "gunicorn app:app --bind 0.0.0.0:$PORT --workers 4 --threads 2 --timeout 120"
```

### 2. `railway.json`
Deployment configuration:

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "gunicorn app:app --bind 0.0.0.0:$PORT --workers 4 --threads 2 --timeout 120",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

## Common Issues & Solutions

### Issue 1: "Browser closed unexpectedly"
**Symptom:** `pyppeteer.errors.BrowserError: Browser closed unexpectedly:`

**Cause:** Chromium is not installed or missing dependencies.

**Solution:**
1. Ensure `nixpacks.toml` exists in the root directory
2. Ensure `chromium` is listed in `nixPkgs`
3. Redeploy on Railway

### Issue 2: "No system browser found"
**Symptom:** `[puppeteer] No system browser found. Will try bundled Chromium (may download).`

**Cause:** Chromium not detected by the auto-detection logic.

**Solution:**
1. Check Railway logs for the actual Chromium path (usually `/nix/store/*/bin/chromium`)
2. Set environment variable in Railway dashboard:
   ```
   PUPPETEER_EXECUTABLE_PATH=/nix/store/.../bin/chromium
   ```
3. Or let the code auto-detect (should work with latest updates)

### Issue 3: Missing dependencies
**Symptom:** Chromium launches but crashes with missing library errors.

**Solution:** Add more packages to `nixpacks.toml`:
```toml
[phases.setup]
nixPkgs = [
  "python311",
  "chromium",
  "nss",
  "nspr",
  "atk",
  "cups",
  "dbus",
  "libdrm",
  "libX11",
  "libxcb",
  "libxkbcommon",
  "mesa"
]
```

## Debugging

### Check Chromium Installation
Add this to your Flask app temporarily:

```python
@app.route('/debug/chromium')
def debug_chromium():
    import subprocess
    import shutil
    
    # Check if chromium is in PATH
    chromium_path = shutil.which('chromium')
    
    # Try to run chromium --version
    try:
        result = subprocess.run(['chromium', '--version'], 
                              capture_output=True, text=True, timeout=5)
        version = result.stdout
    except Exception as e:
        version = f"Error: {e}"
    
    return {
        'chromium_in_path': chromium_path,
        'chromium_version': version,
        'PATH': os.environ.get('PATH', ''),
        'nix_store_chromium': glob.glob('/nix/store/*/bin/chromium')
    }
```

### Enable Verbose Logging
Set environment variable in Railway:
```
WXIMG_DEBUG=1
```

## Testing Locally (Development)

### Without Docker
```bash
# Install Chromium on your system
# macOS: brew install chromium
# Ubuntu/Debian: apt install chromium-browser
# Windows: Download from google.com/chrome

# Run locally
python launch_web_interface.py
```

### With Docker (simulate Railway)
```dockerfile
FROM nixos/nix

# Install Nix packages
RUN nix-env -iA nixpkgs.python311 nixpkgs.chromium

# Copy app
COPY . /app
WORKDIR /app

# Install Python deps
RUN pip install -r requirements.txt

# Run
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:8000"]
```

## Environment Variables

Required on Railway:
- `PORT` - Auto-set by Railway
- `OPENROUTER_API_KEY` - Your OpenRouter API key
- `GOOGLE_PSE_KEY` - Google Programmable Search Engine key (optional)
- `GOOGLE_PSE_ID` - Google PSE ID (optional)

Optional:
- `WXIMG_DEBUG` - Enable debug logging for image generation
- `PUPPETEER_EXECUTABLE_PATH` - Manual override for Chromium path

## Resource Requirements

Recommended Railway plan:
- **Memory:** At least 1GB (2GB+ recommended for multiple workers)
- **CPU:** Shared is fine, but dedicated is better for image generation
- **Storage:** 512MB+ (for Chromium + fonts)

## Performance Optimization

1. **Reduce workers:** If memory is limited, use fewer Gunicorn workers:
   ```
   --workers 2 --threads 2
   ```

2. **Reduce device scale:** Lower quality but faster:
   ```python
   device_scale=2  # instead of 4
   ```

3. **Add timeout:** Prevent stuck requests:
   ```
   --timeout 120
   ```

## Contact & Support

If issues persist:
1. Check Railway build logs
2. Check Railway deployment logs
3. Enable `WXIMG_DEBUG=1` for verbose output
4. Test the `/debug/chromium` endpoint (if implemented)

