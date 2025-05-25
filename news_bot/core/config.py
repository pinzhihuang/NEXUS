# news_bot/core/config.py

import os
from dotenv import load_dotenv
from datetime import timedelta


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOTENV_PATH = os.path.join(PROJECT_ROOT, '.env')
load_dotenv(DOTENV_PATH)


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") # For PSE and Search
CUSTOM_SEARCH_ENGINE_ID = os.getenv("CUSTOM_SEARCH_ENGINE_ID")
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")

GEMINI_FLASH_MODEL = os.getenv("GEMINI_FLASH_MODEL", 'gemini-2.5-flash-preview-05-20') 
GEMINI_SUMMARY_MODEL = os.getenv("GEMINI_SUMMARY_MODEL", 'gemini-2.5-flash-preview-05-20')
GEMINI_FLASH_MODEL_CONTEXT_LIMIT_CHARS = int(os.getenv("GEMINI_FLASH_MODEL_CONTEXT_LIMIT_CHARS", "150000"))

GEMINI_SUMMARY_MODEL_CONTEXT_LIMIT_CHARS = int(os.getenv("GEMINI_SUMMARY_MODEL_CONTEXT_LIMIT_CHARS", "150000"))

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


TARGET_NEWS_SOURCES_DOMAINS = [
    "nyunews.com", 
    "www.nyu.edu/news"
]
CATEGORY_PAGES_TO_SCAN = [
    #"https://nyunews.com/category/news/"
    # nypost 
    "https://www.nyu.edu/about/news-publications/news.html"

]
RELEVANCE_KEYWORDS = [
    "Chinese international students", "NYU News","New York student life", "NYU campus events"
]

# Article Processing Configuration
RECENCY_THRESHOLD_DAYS = int(os.getenv("RECENCY_THRESHOLD_DAYS", "7"))
RECENCY_TIMEDELTA = timedelta(days=RECENCY_THRESHOLD_DAYS)
URL_FETCH_TIMEOUT = int(os.getenv("URL_FETCH_TIMEOUT", "20")) # seconds

# Output Configuration
DEFAULT_OUTPUT_DIR = os.getenv("DEFAULT_OUTPUT_DIR", "news_reports")
MAX_FINAL_REPORTS = int(os.getenv("MAX_FINAL_REPORTS", "5"))
MAX_SEARCH_RESULTS_TO_PROCESS = int(os.getenv("MAX_SEARCH_RESULTS_TO_PROCESS", "10"))

def validate_config():
    """Validates that essential configurations are set."""
    errors = []
    if not GEMINI_API_KEY:
        errors.append("GEMINI_API_KEY is not set.")
    if not GOOGLE_API_KEY: # For PSE
        errors.append("GOOGLE_API_KEY is not set (for Custom Search).")
    if not CUSTOM_SEARCH_ENGINE_ID:
        errors.append("CUSTOM_SEARCH_ENGINE_ID (CX ID) is not set (for Custom Search).")
    
    # Check for OAuth credentials file if Docs export is intended
    # This is a soft check here; the exporter module will handle it more gracefully
    if not os.path.exists(OAUTH_CREDENTIALS_FILE):
        print(f"Warning: OAuth credentials file (for Google Docs) not found at {OAUTH_CREDENTIALS_FILE}. Google Docs export will fail if this feature is used.")

    if errors:
        error_message = "Configuration errors found:\n" + "\n".join(errors) + \
                        f"\nPlease ensure your .env file and credentials files are correctly set up."
        raise ValueError(error_message)
    
    dotenv_status_message = f"successfully from {DOTENV_PATH}" if os.path.exists(DOTENV_PATH) else "from environment variables (or .env not found/readable)"
    print(f"Configuration loaded {dotenv_status_message}.")
    print(f"  GEMINI_FLASH_MODEL: {GEMINI_FLASH_MODEL}")
    print(f"  GEMINI_SUMMARY_MODEL: {GEMINI_SUMMARY_MODEL}")
    print(f"  Output directory: {DEFAULT_OUTPUT_DIR}")
    if TARGET_GOOGLE_DOC_ID:
        print(f"  Target Google Doc ID for updates: {TARGET_GOOGLE_DOC_ID}")
    else:
        print("  Target Google Doc ID not set; new doc will be created on each export.")

if not all([GEMINI_API_KEY, GOOGLE_API_KEY, CUSTOM_SEARCH_ENGINE_ID]):
    if os.path.exists(DOTENV_PATH):
        print(f"Warning: Attempted to load .env from {DOTENV_PATH}, but one or more API keys (GEMINI, GOOGLE_API_KEY for PSE, CUSTOM_SEARCH_ENGINE_ID) are still missing from the environment.")
    else:
        print(f"Warning: .env file not found at {DOTENV_PATH}. Critical API keys might be missing.") 