# Railway Deployment Checklist

## Files Created for Railway Deployment

✅ **Procfile** - Defines how Railway starts your web server
- Uses gunicorn with 4 workers and 2 threads
- Binds to 0.0.0.0:$PORT (Railway provides PORT automatically)

✅ **runtime.txt** - Specifies Python version (3.11.9)

✅ **railway.json** - Railway build and deploy configuration
- Automatically installs pyppeteer and Chromium for image generation
- Configures restart policy for reliability

✅ **.env.example** - Template for environment variables
- Shows all required and optional variables
- Use this as a reference when setting up Railway environment

✅ **app.py** - Updated for production deployment
- Reads PORT from environment variable
- Binds to 0.0.0.0 for Railway
- Checks FLASK_ENV for production/development mode

## Deployment Steps

### 1. Push to GitHub
```bash
git add .
git commit -m "Add Railway deployment configuration"
git push origin main
```

### 2. Deploy on Railway

1. Go to [Railway.app](https://railway.app) and sign in
2. Click "New Project" → "Deploy from GitHub repo"
3. Select your repository
4. Railway will auto-detect the configuration

### 3. Set Environment Variables

In Railway Dashboard → Your Project → Variables, add:

**Required:**
```
OPENROUTER_API_KEY=sk-or-v1-YOUR_KEY_HERE
```

**Optional (for advanced features):**
```
GOOGLE_API_KEY=YOUR_GOOGLE_API_KEY
CUSTOM_SEARCH_ENGINE_ID=YOUR_PSE_ID
TARGET_GOOGLE_DOC_ID=YOUR_DOC_ID
SECRET_KEY=random-secret-key-change-this
```

### 4. Deploy!

Railway will automatically:
- Install Python 3.11.9
- Install all dependencies from requirements.txt
- Install Chromium via pyppeteer
- Start the web server using gunicorn

### 5. Access Your App

Railway will provide a URL like: `https://your-app.railway.app`

## What Changed for Railway

### app.py
- Now reads `PORT` from environment (Railway requirement)
- Binds to `0.0.0.0` instead of `127.0.0.1` (for external access)
- Checks `FLASK_ENV` to disable debug mode in production

### Build Process
- `railway.json` ensures Chromium is installed for image generation
- `Procfile` uses gunicorn instead of Flask development server
- Multiple workers/threads for better performance

### Environment Variables
- All secrets moved to environment variables (not in code)
- `.env.example` provides clear documentation
- Railway Dashboard makes it easy to manage variables

## Verification

After deployment, test these features:
1. ✅ Homepage loads at your Railway URL
2. ✅ Can start a news collection job
3. ✅ Can view and edit generated reports
4. ✅ Can generate WeChat-style images
5. ✅ Can download images as ZIP

## Troubleshooting

### Check Railway Logs
Railway Dashboard → Your Project → Deployments → View Logs

Common issues:
- **Missing OPENROUTER_API_KEY**: Add it in Variables tab
- **Chromium not found**: Check build logs for pyppeteer-install
- **Port binding error**: Ensure app.py uses PORT from environment
- **Import errors**: Check all dependencies in requirements.txt

### Need Help?
- Railway Docs: https://docs.railway.app
- Railway Discord: https://discord.gg/railway
- Project Issues: Create an issue in your GitHub repo

## Cost Estimate

Railway Pricing (as of 2024):
- **Free Tier**: $5 credit/month (enough for testing)
- **Hobby Plan**: $5/month + usage
- **Pro Plan**: $20/month + usage

This app uses:
- Minimal compute (web server is lightweight)
- No database needed
- Most cost comes from OpenRouter API calls

Estimated monthly cost: $5-15 depending on usage

