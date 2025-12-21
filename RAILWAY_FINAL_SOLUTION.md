# Railway Deployment Fix - Final Solution

## Problem History

### Issue 1: Health Check Timeout
- **Symptom**: Health check failing with "service unavailable"
- **Cause**: Slow imports and `preload_app=True`
- **Fix**: Removed blocking code, disabled preload
- ✅ **Status**: Fixed

### Issue 2: Gunicorn Not Found
- **Symptom**: `❌ ERROR: gunicorn NOT FOUND`
- **Cause**: Overriding `[phases.install]` in nixpacks.toml broke automatic pip install
- **Attempted Fix**: Manually added `pip install` command
- ❌ **Result**: `pip: command not found`

### Issue 3: Pip Not Found (Current)
- **Symptom**: `/bin/bash: line 1: pip: command not found`
- **Root Cause**: Overriding `[phases.install]` prevents Nixpacks from setting up Python environment
- **Solution**: Remove the `[phases.install]` override entirely

## The Correct Fix

**`nixpacks.toml`** should be minimal - only add chromium, let Nixpacks handle Python:

```toml
# Nixpacks configuration for Railway deployment
# Adds Chromium for headless browser support

[phases.setup]
# Add chromium to the base Nix packages
# "..." means keep all default packages that Nixpacks would include
nixPkgs = ["...", "chromium"]

# Don't override [phases.install] - let Nixpacks auto-detect Python and run pip install
# Nixpacks will automatically run: pip install -r requirements.txt

[start]
cmd = "bash -x start.sh 2>&1"
```

## Why This Works

1. **`[phases.setup]`** with `nixPkgs = ["...", "chromium"]`:
   - The `"..."` keeps all default Nix packages (including Python, pip, etc.)
   - Adds chromium on top of the defaults

2. **No `[phases.install]` override**:
   - Nixpacks auto-detects Python from `requirements.txt`
   - Sets up Python environment automatically
   - Runs `pip install -r requirements.txt` automatically
   - Installs all dependencies including gunicorn

3. **`[start]` with custom command**:
   - Runs your `start.sh` script which launches gunicorn

## Deploy

```bash
git add nixpacks.toml
git commit -m "Fix: Let Nixpacks auto-detect Python, only add chromium"
git push railway main
```

## Expected Behavior

Railway build will:
1. ✅ Detect Python project from `requirements.txt`
2. ✅ Set up Python environment (includes pip)
3. ✅ Run `pip install -r requirements.txt` automatically
4. ✅ Install all packages including gunicorn, Flask, etc.
5. ✅ Add chromium from Nix packages
6. ✅ Start container with `bash start.sh`
7. ✅ Gunicorn launches successfully
8. ✅ Health check passes
9. ✅ Deployment succeeds! 🎉

---

## Key Lesson

**Don't override Nixpacks phases unless absolutely necessary!** When you override `[phases.install]`, you take full responsibility for setting up the environment. It's better to let Nixpacks do what it does best (auto-detecting languages and installing dependencies) and only customize the parts you need (adding chromium).

**Status**: ✅ **FINAL FIX APPLIED**

