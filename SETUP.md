# Quick Setup Guide for USC News

## Required Setup

### 1. Create `.env` file

Create a `.env` file in the project root directory.

### 2. Get OpenRouter API Key

**Get your OpenRouter API Key:**
1. Go to https://openrouter.ai/
2. Sign in or create an account
3. Navigate to https://openrouter.ai/keys
4. Click "Create Key" or use an existing key
5. Copy the API key (starts with `sk-or-v1-...`)

**Important:** OpenRouter requires credits for API usage. Make sure you have sufficient credits:
- Free tier includes some credits
- Visit https://openrouter.ai/settings/credits to check your balance
- You may need to add credits for production use

### 3. Configure `.env` file

Edit `.env` and add your **OPENROUTER_API_KEY**:

```env
OPENROUTER_API_KEY="sk-or-v1-your_actual_openrouter_api_key_here"
```

**Optional:** You can also configure model names (defaults are already set):
```env
GEMINI_FLASH_MODEL="google/gemini-2.5-flash"
GEMINI_PRO_MODEL="google/gemini-2.5-pro"
```

### 4. Optional: Google Docs Export (credentials.json)

If you want to export news to Google Docs, you need `credentials.json`:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable "Google Docs API"
4. Go to "Credentials" → "Create Credentials" → "OAuth client ID"
5. Choose "Desktop app" as application type
6. Download the JSON file
7. Rename it to `credentials.json` and place it in the project root (`/Users/edwinhuang/NEXUS-3/`)

**Note:** On first run, a browser will open for OAuth authorization.

## Running USC News Collection

Once `.env` is set up with `OPENROUTER_API_KEY`:

```bash
python -m news_bot.main_orchestrator
```

When prompted, select **5** for USC.

## What Changed

- ✅ **Updated:** Now uses OpenRouter API instead of direct Gemini API
- ✅ **Fixed:** Google PSE keys are now optional (only warnings, not errors)
- ✅ **Fixed:** Only `OPENROUTER_API_KEY` is required for USC news
- ✅ **Fixed:** USC-specific prompts now work correctly (no more NYU hardcoding)

## Troubleshooting

**Error: "OPENROUTER_API_KEY is not set"**
- Make sure `.env` file exists in the project root
- Check that the key is properly quoted: `OPENROUTER_API_KEY="your_key_here"`
- No spaces around the `=` sign

**Error: "402 Payment Required" or "requires more credits"**
- Your OpenRouter account needs more credits
- Visit https://openrouter.ai/settings/credits to add credits
- Free tier includes some credits, but you may need to upgrade for production use
- Check your credit balance at https://openrouter.ai/settings/credits

**Warning: "OAuth credentials file not found"**
- This is OK if you don't need Google Docs export
- News will still be saved to JSON files in `news_reports/` folder
