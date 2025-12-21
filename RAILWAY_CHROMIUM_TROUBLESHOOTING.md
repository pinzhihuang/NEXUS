# Railway Chromium Fix - Complete Guide

## Problem
Chromium fails to launch on Railway with error: "Browser closed unexpectedly"

## Root Cause
The pyppeteer bundled Chromium doesn't work in Railway's environment. We need to use the system Chromium installed via Nixpacks.

## Solution Applied

### 1. Enhanced nixpacks.toml
- Added Chromium and all required dependencies (nss, freetype, harfbuzz, ca-certificates, ttf-freefont, fontconfig)
- Added debug commands to verify Chromium installation during build

### 2. Updated image_generator.py
- Enhanced `_guess_chrome_path()` with detailed logging
- Prioritized Nix store paths for Railway
- Added comprehensive Chrome launch arguments for headless environments

### 3. Created railway_setup.sh
- Bash script that finds Chromium in Railway environment
- Exports PUPPETEER_EXECUTABLE_PATH automatically
- Runs during app startup (called from start.sh)

### 4. Updated start.sh
- Calls railway_setup.sh before starting Gunicorn
- Provides detailed debugging output

## Expected Railway Build Logs

You should see during deployment:

```
=== Running Chromium Setup ===
🔍 Railway Chromium Setup
==========================
✅ Found in Nix store: /nix/store/XXXX-chromium-XXX/bin/chromium
✅ Exported PUPPETEER_EXECUTABLE_PATH=/nix/store/XXXX-chromium-XXX/bin/chromium
✅ Chromium is working: Chromium 120.0.6099.109
==========================
```

## Expected Runtime Logs

When generating images, you should see:

```
[chrome_path] Found 1 Nix Chromium paths
[chrome_path]   - /nix/store/XXXX-chromium-XXX/bin/chromium
[chrome_path] Checking X candidate paths...
[chrome_path] ✅ Found working path: /nix/store/XXXX-chromium-XXX/bin/chromium
[puppeteer] Using system browser: /nix/store/XXXX-chromium-XXX/bin/chromium
```

## If Still Failing

### Check 1: Verify Chromium in Build Logs
Look for during Railway build:
- "installing 'chromium'"
- "chromium --version" output showing version

### Check 2: Manually Set Path
If auto-detection fails, add this Railway environment variable:
```
PUPPETEER_EXECUTABLE_PATH=/nix/store/HASH-chromium-VERSION/bin/chromium
```

Find the exact path from build logs.

### Check 3: Test Locally with Docker
```bash
docker run -it nixos/nix
nix-shell -p chromium python311
chromium --version
```

## Alternative: Use Playwright (Future)

If pyppeteer continues to fail, consider switching to Playwright:
```bash
pip install playwright
playwright install chromium
```

Playwright has better Railway support but requires code changes.

## Files Modified
- `nixpacks.toml` - Nix packages configuration
- `news_bot/processing/image_generator.py` - Enhanced path detection
- `railway_setup.sh` - NEW: Chromium finder script
- `start.sh` - Runs setup script before Gunicorn

## Testing Steps
1. Push changes to GitHub
2. Railway redeploys automatically
3. Check build logs for Chromium installation
4. Check runtime logs for path detection
5. Try generating images via web interface
6. Should succeed without "Browser closed unexpectedly" error

