# 🚀 Railway Deployment Guide - Project NEXUS

## Quick Deploy to Railway

### Step 1: Prepare Files (Already Done ✅)

These files configure Railway deployment:
- `nixpacks.toml` - Installs Chromium for image generation
- `railway.json` - Build and deploy configuration  
- `Procfile` - Server startup command
- `runtime.txt` - Python version
- `requirements.txt` - Python dependencies

### Step 2: Push to GitHub

```bash
git add .
git commit -m "Add Railway deployment with Chromium support"
git push origin main
```

### Step 3: Deploy on Railway

1. Go to [railway.app](https://railway.app) and sign in with GitHub
2. Click "New Project" → "Deploy from GitHub repo"
3. Select your repository
4. Railway will auto-detect configuration and deploy

### Step 4: Set Environment Variables

In Railway Dashboard → Your Project → Variables, add:

**Required:**
```
OPENROUTER_API_KEY=sk-or-v1-YOUR_KEY_HERE
```

**Optional:**
```
GOOGLE_API_KEY=YOUR_GOOGLE_API_KEY
CUSTOM_SEARCH_ENGINE_ID=YOUR_PSE_ID
SECRET_KEY=random-secret-key
```

### Step 5: Test Your Deployment

1. Railway provides a URL like: `https://your-app.railway.app`
2. Test image generation: `/api/debug/chromium` should show Chromium installed
3. Run a news collection job and generate images

---

## What's Configured for Railway

### Chromium Installation (`nixpacks.toml`)
```toml
[phases.setup]
nixPkgs = ["...", "chromium"]
aptPkgs = ["chromium", "chromium-driver"]
```

This ensures Chromium is available for WeChat-style image generation.

### Build Configuration (`railway.json`)
- Uses Nixpacks builder (auto-detects Python)
- Starts with Gunicorn (production server)
- 4 workers, 2 threads per worker
- 120-second timeout for long-running requests
- Auto-restart on failure

### Debug Endpoint
Visit `/api/debug/chromium` to verify Chromium installation:
```json
{
  "auto_detected_path": "/nix/store/.../bin/chromium",
  "chromium_version": "Chromium 120.0.6099.109",
  "executables": {
    "chromium": "/nix/store/.../bin/chromium"
  }
}
```

---

## Troubleshooting

### "Browser closed unexpectedly" Error

**Cause:** Chromium not installed properly

**Solution:**
1. Check Railway build logs for "installing 'chromium'"
2. Visit `/api/debug/chromium` to verify Chromium path
3. If not found, set environment variable:
   ```
   PUPPETEER_EXECUTABLE_PATH=/nix/store/HASH/bin/chromium
   ```

### Build Fails with "pip: command not found"

**Cause:** Custom nixpacks.toml interfering with Python setup

**Solution:** The current `nixpacks.toml` uses `"..."` to keep Railway's auto-detected Python setup and just adds Chromium.

### Images Not Generating

**Check these:**
1. Chromium installed: `/api/debug/chromium`
2. Railway logs show: `[puppeteer] Using system browser`
3. No timeout errors (increase timeout if needed)

---

## Cost Estimate

Railway Pricing:
- **Free Trial:** $5 credit
- **Hobby Plan:** $5/month + usage

Estimated costs:
- **Light use** (weekly jobs): ~$2-3/month
- **Medium use** (daily jobs): ~$5-8/month  
- **Heavy use** (multiple daily): ~$10-15/month

---

## Performance Tips

1. **Reduce workers** if memory limited:
   ```
   --workers 2 --threads 2
   ```

2. **Lower image quality** for faster generation:
   ```python
   device_scale=2  # instead of 4
   ```

3. **Monitor usage** in Railway dashboard

---

## Need Help?

- Check Railway deployment logs
- Check Railway application logs  
- Test `/api/debug/chromium` endpoint
- Enable verbose logging: `WXIMG_DEBUG=1`

**You're now deployed! 🎉**
