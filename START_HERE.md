# 🚀 Project NEXUS - Web Interface Guide

> **The easiest way to collect and translate university news for Chinese international students**

## What This Is

✨ **A beautiful web interface for your news bot!**

Instead of typing commands in a terminal, you now have:
- 🎨 Beautiful purple gradient dashboard
- 📊 Real-time progress tracking with live updates
- 📱 Works on any device (desktop, tablet, phone)
- 🚀 Just 3 clicks to start collecting news
- 🌏 Automatic translation from English to Chinese

## The Absolute Quickest Way to Start

### Option 1: Auto-Launch (Opens Browser Automatically)
```bash
python launch_web_interface.py
```
This will:
- Check everything is installed
- Start the server
- Open your browser automatically

### Option 2: Manual Launch
```bash
python app.py
```
Then open your browser to: **http://127.0.0.1:5000**

## First Time Setup (2 Minutes)

### 1. Install Flask
```bash
pip install Flask
```

### 2. Set Your API Key (Required for news collection)
Create a file named `.env` in the project folder:
```
OPENROUTER_API_KEY=your_api_key_here
```

Get your API key from: https://openrouter.ai/keys

### 3. Start Using It!
```bash
python launch_web_interface.py
```

## Using the Web Interface

### It's Super Simple:

1. **Open browser** → http://127.0.0.1:5000

2. **Select university** (e.g., New York University)

3. **Pick date range** (or use default: last 7 days)

4. **Click the big purple button** → "🚀 Start News Collection"

5. **Watch it work!**
   - Progress bar shows completion
   - Statistics update in real-time
   - Activity log shows each step

6. **Review your results!**
   - See all collected articles with Chinese translations
   - Each article shows:
     - Chinese title (AI-generated)
     - Chinese news report (professional translation)
     - Original English title
     - Source URL and publication date

7. **Optional: Generate WeChat Images**
   - Click "🎨 Generate WeChat Images" button
   - Creates beautiful WeChat-style images directly from JSON
   - Images are saved to `wechat_images/<School_Weekly>/` folder
   - Perfect for sharing on WeChat, social media, or newsletters
   - No Google Docs required - works directly from JSON!

8. **Get your results!**
   - **JSON file:** `news_reports/` folder (always saved)
   - **WeChat Images:** `wechat_images/` folder (optional, click button to generate)

## What the Program Does

**Project NEXUS** automatically:

1. 🔍 **Finds** news articles from university websites
2. ✅ **Verifies** they're relevant and recent (using AI)
3. 📝 **Summarizes** in English (using AI)
4. 🌏 **Translates** to Chinese (using AI)
5. 💾 **Saves** as JSON files

**Purpose:** Help Chinese international students stay informed about campus news in their native language.

## Files You Got

### Core Files:
- `app.py` - The Flask web server
- `templates/index.html` - The beautiful interface
- `launch_web_interface.py` - Easy launcher with auto-open browser

### Documentation:
- `START_HERE.md` - This file (everything you need!)
- `README.md` - Original project documentation
- `SETUP.md` - Original setup instructions

## Supported Universities

Choose from 6 universities:
- 🎓 New York University (NYU)
- 🎓 Emory University
- 🎓 University of California, Davis
- 🎓 University of British Columbia
- 🎓 University of Southern California
- 🎓 University of Edinburgh

## Typical Results

**What you'll get for "last 7 days" at NYU:**
- 10-20 news articles
- Each with:
  - Original English title
  - Source URL
  - Publication date
  - English summary (200-300 words)
  - Chinese title
  - Chinese report (professional translation)
  - Verification details

**Processing time:** 2-5 minutes

## Common Questions

### "Do I need to install anything?"
Just Flask: `pip install Flask`  
Everything else is already in requirements.txt

### "Where do I get an API key?"
https://openrouter.ai/keys (required for AI features)

### "Can I use this without terminal commands?"
Yes! That's the whole point! Just open your browser.

### "Does the old CLI still work?"
Yes! Both work. Use whatever you prefer.

### "Is this safe?"
Yes! Runs on your computer only (localhost). Not exposed to internet.

### "What if I get an error?"
1. Run `python test_setup.py` to diagnose
2. Check the documentation files
3. Look at the activity log in the web interface

## Quick Troubleshooting

### "OPENROUTER_API_KEY is not set"
Create `.env` file with your API key

### "Port 5000 already in use"
Change port in `app.py` line 287: `port=5001`

### "Module 'flask' not found"
Install Flask: `pip install Flask`

### "No articles found"
Normal during university breaks. Try different dates or school.

## What Makes This Amazing

### Before (CLI):
```
$ python -m news_bot.main_orchestrator
=== Project NEXUS - Student News Bot - Starting Run ===
=== Please pick a school to collect news from: ===
  1: New York University (NYU)
  2: Emory University
  ...
Please enter the ID of the school: _
```
😓 Confusing, text-only, no feedback

### After (Web Interface):
```
Beautiful purple gradient dashboard
Big dropdown: "Select University"
Date pickers with calendar
Big button: "Start News Collection"
Live progress bar: ████████████ 65%
Statistics: 15 found, 8 processed, 5 generated
Activity log with emojis and timestamps
```
🎉 Simple, visual, real-time feedback!

## Performance

- **Startup:** <1 second
- **Processing:** 2-5 minutes (depends on article count)
- **Browser load:** <2 seconds
- **Memory:** ~500MB during processing

## Technical Details (If You Care)

- **Framework:** Flask (Python web framework)
- **Frontend:** Vanilla HTML/CSS/JavaScript
- **Real-time Updates:** Server-Sent Events
- **Background Processing:** Threading
- **AI Models:** Google Gemini via OpenRouter
- **Export:** JSON files only (simple and reliable)

## Next Steps

### To Start Using Now (Local):
```bash
python launch_web_interface.py
```

### To Deploy to Cloud:
See `DEPLOYMENT.md` for comprehensive cloud deployment guides:
- ☁️ Tencent Cloud (Recommended for China)
- 🚂 Railway (Easy international deployment)
- 🐳 Docker/Docker Compose
- And more options!

### To Learn More:
- Read this entire file (you're almost done!)
- Check the original `README.md` for project background
- Review `SETUP.md` for advanced configuration

### To Customize:
- Edit `templates/index.html` for UI
- Edit `app.py` for logic
- Edit `.env` for settings

## Support

If something doesn't work:
1. Check the activity log in the web interface
2. Make sure Flask is installed: `pip install Flask`
3. Verify your `.env` file has OPENROUTER_API_KEY
4. Review `prompt_logs/` folder for detailed AI logs

## That's It!

You now have everything you need. The interface is designed to be **self-explanatory**.

**Try it right now:**
```bash
python launch_web_interface.py
```

Then go to: **http://127.0.0.1:5000**

**Enjoy your beautiful new interface! 🚀**

---

*Made with ❤️ for Chinese international students*

