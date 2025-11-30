# news_bot/core/config.py

import os
from dotenv import load_dotenv
from datetime import datetime, date, timedelta


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOTENV_PATH = os.path.join(PROJECT_ROOT, '.env')
load_dotenv(DOTENV_PATH)


# OpenRouter API Configuration
# Get your API key from https://openrouter.ai/keys
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Legacy Gemini API Key (deprecated, kept for backward compatibility)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") # For PSE and Search
CUSTOM_SEARCH_ENGINE_ID = os.getenv("CUSTOM_SEARCH_ENGINE_ID")
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")

# Model names for OpenRouter (using Google Gemini models via OpenRouter)
GEMINI_FLASH_MODEL = os.getenv("GEMINI_FLASH_MODEL", 'google/gemini-2.5-flash') 
GEMINI_SUMMARY_MODEL = os.getenv("GEMINI_SUMMARY_MODEL", 'google/gemini-2.5-flash')
GEMINI_PRO_MODEL = os.getenv("GEMINI_PRO_MODEL", 'google/gemini-2.5-pro')
GEMINI_FLASH_MODEL_CONTEXT_LIMIT_CHARS = int(os.getenv("GEMINI_FLASH_MODEL_CONTEXT_LIMIT_CHARS", "150000"))

GEMINI_SUMMARY_MODEL_CONTEXT_LIMIT_CHARS = int(os.getenv("GEMINI_SUMMARY_MODEL_CONTEXT_LIMIT_CHARS", "150000"))
GEMINI_PRO_MODEL_CONTEXT_LIMIT_CHARS = int(os.getenv("GEMINI_PRO_MODEL_CONTEXT_LIMIT_CHARS", "2000000"))  # Pro model has much larger context

# Perplexity API Configuration (Optional -- This logic has been abandoned. Perplexity is a piece of shit. Google is not going to be replaced by Perplexity.) 
PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"
PERPLEXITY_SEARCH_MODEL = os.getenv("PERPLEXITY_SEARCH_MODEL", "sonar-pro") 

# Google OAuth Credentials for Docs API (Desktop App Flow)
# Path to the credentials.json file downloaded from Google Cloud Console
OAUTH_CREDENTIALS_FILE = os.path.join(PROJECT_ROOT, os.getenv("OAUTH_CREDENTIALS_FILENAME", "credentials.json"))
# Path to store the token.pickle file after successful authorization
OAUTH_TOKEN_PICKLE_FILE = os.path.join(PROJECT_ROOT, os.getenv("OAUTH_TOKEN_FILENAME", "token.pickle"))
GOOGLE_DOCS_SCOPES = ['https://www.googleapis.com/auth/documents'] # Scope for creating/editing docs
TARGET_GOOGLE_DOC_ID = os.getenv("TARGET_GOOGLE_DOC_ID", None)

# Gmail API Credentials
GMAIL_SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
OAUTH_TOKEN_PICKLE_FILE_GMAIL = os.path.join(PROJECT_ROOT, os.getenv("OAUTH_TOKEN_FILENAME_GMAIL", "gmail_token.pickle"))


# Legacy config
TARGET_NEWS_SOURCES_DOMAINS = [
    "nyunews.com", 
    "www.nyu.edu/news"
]
CATEGORY_PAGES_TO_SCAN = [
    "https://nyunews.com/category/news/"
]
# Archive URL patterns for date-specific searches
# Use {year}, {month}, {day} as placeholders
# Note: These patterns should be adjusted based on the actual archive structure of the target sites
ARCHIVE_URL_PATTERNS = [
    # WSN might use patterns like: /2025/02/ for February 2025 archives
    "https://nyunews.com/{year}/{month:02d}/",
    # NYU news might have monthly archive pages
    "https://www.nyu.edu/about/news-publications/news/{year}/{month:02d}.html",
    # Alternative patterns to try
    "https://nyunews.com/news/{year}/{month:02d}/",
]

# =============================================================================
# DATE RANGE CONFIGURATION FOR NEWS COLLECTION
# =============================================================================
# NEWS_START_DATE: Specify the starting date for news collection
# - Format: "YYYY-MM-DD" (e.g., "2024-07-25")
# - If not set or None, defaults to (current date - RECENCY_THRESHOLD_DAYS)
# - The program will collect news from this date + RECENCY_THRESHOLD_DAYS forward
# 
# RECENCY_THRESHOLD_DAYS: Number of days to collect news from the start date
# - Default: 7 (one week)
# - Example: If NEWS_START_DATE="2024-07-25" and RECENCY_THRESHOLD_DAYS=7,
#           the program will collect news from July 25-31, 2024
# =============================================================================

# Parse NEWS_START_DATE from environment or use None for automatic calculation
NEWS_START_DATE_STR = os.getenv("NEWS_START_DATE", None)
if NEWS_START_DATE_STR:
    try:
        NEWS_START_DATE = datetime.strptime(NEWS_START_DATE_STR, "%Y-%m-%d").date()
        print(f"Using custom news start date: {NEWS_START_DATE}")
    except ValueError:
        print(f"Warning: Invalid NEWS_START_DATE format '{NEWS_START_DATE_STR}'. Expected YYYY-MM-DD. Using default.")
        NEWS_START_DATE = None
else:
    NEWS_START_DATE = None

# Number of days to collect news (from start date forward)
RECENCY_THRESHOLD_DAYS = int(os.getenv("RECENCY_THRESHOLD_DAYS", "7"))  # Default to 7 days (one week)
RECENCY_TIMEDELTA = timedelta(days=RECENCY_THRESHOLD_DAYS)

# Calculate effective date range for news collection
def get_news_date_range():
    """
    Returns a tuple of (start_date, end_date) for news collection.
    If NEWS_START_DATE is set, uses it as the start date.
    Otherwise, uses (today - RECENCY_THRESHOLD_DAYS + 1) as start date.
    """
    if NEWS_START_DATE:
        # User specified a custom start date
        start_date = NEWS_START_DATE
        end_date = start_date + timedelta(days=RECENCY_THRESHOLD_DAYS - 1)
    else:
        # Default behavior: collect news from the past RECENCY_THRESHOLD_DAYS
        end_date = date.today()
        start_date = end_date - timedelta(days=RECENCY_THRESHOLD_DAYS - 1)
    
    return start_date, end_date

# Article Processing Configuration
URL_FETCH_TIMEOUT = int(os.getenv("URL_FETCH_TIMEOUT", "20")) # seconds

# Output Configuration
DEFAULT_OUTPUT_DIR = os.getenv("DEFAULT_OUTPUT_DIR", "news_reports")
MAX_FINAL_REPORTS = int(os.getenv("MAX_FINAL_REPORTS", "20"))
MAX_SEARCH_RESULTS_TO_PROCESS = int(os.getenv("MAX_SEARCH_RESULTS_TO_PROCESS", "120"))
MAX_CATEGORY_PAGES_TO_SCAN = int(os.getenv("MAX_CATEGORY_PAGES_TO_SCAN", "20"))

def validate_config():
    """Validates that essential configurations are set."""
    errors = []
    if not OPENROUTER_API_KEY:
        errors.append("OPENROUTER_API_KEY is not set (required for article verification and summarization).")
    # Google PSE is currently disabled in search_client.py, so these are optional
    if not GOOGLE_API_KEY: # For PSE (optional - currently disabled)
        print("Warning: GOOGLE_API_KEY is not set (for Custom Search). Google PSE search is currently disabled, so this is optional.")
    if not CUSTOM_SEARCH_ENGINE_ID: # For PSE (optional - currently disabled)
        print("Warning: CUSTOM_SEARCH_ENGINE_ID (CX ID) is not set (for Custom Search). Google PSE search is currently disabled, so this is optional.")
    
    # Note: Google Docs export has been removed - we only use JSON now

    if errors:
        error_message = "Configuration errors found:\n" + "\n".join(errors) + \
                        f"\nPlease ensure your .env file and credentials files are correctly set up."
        raise ValueError(error_message)
    
    dotenv_status_message = f"successfully from {DOTENV_PATH}" if os.path.exists(DOTENV_PATH) else "from environment variables (or .env not found/readable)"
    print(f"Configuration loaded {dotenv_status_message}.")
    print(f"  GEMINI_FLASH_MODEL: {GEMINI_FLASH_MODEL}")
    print(f"  GEMINI_SUMMARY_MODEL: {GEMINI_SUMMARY_MODEL}")
    print(f"  GEMINI_PRO_MODEL: {GEMINI_PRO_MODEL}")
    print(f"  Output directory: {DEFAULT_OUTPUT_DIR}")
    
    # Display date range configuration
    start_date, end_date = get_news_date_range()
    print(f"  News collection date range: {start_date} to {end_date} ({RECENCY_THRESHOLD_DAYS} days)")
    if NEWS_START_DATE:
        print(f"  Using custom start date from configuration")
    else:
        print(f"  Using automatic date range (last {RECENCY_THRESHOLD_DAYS} days)")
    
    # Google Docs export removed - using JSON only

# Only OPENROUTER_API_KEY is required; Google PSE keys are optional since PSE is disabled
if not OPENROUTER_API_KEY:
    if os.path.exists(DOTENV_PATH):
        print(f"Warning: Attempted to load .env from {DOTENV_PATH}, but OPENROUTER_API_KEY is still missing from the environment.")
    else:
        print(f"Warning: .env file not found at {DOTENV_PATH}. Critical API keys might be missing.")