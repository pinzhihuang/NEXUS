# news_bot/core/config.py

import os
from dotenv import load_dotenv
from datetime import timedelta

# Determine the path to the .env file, assuming it's in the project root
# Project root is parent of 'news_bot' directory, which is parent of 'core' directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOTENV_PATH = os.path.join(PROJECT_ROOT, '.env')
load_dotenv(DOTENV_PATH)

# API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
CUSTOM_SEARCH_ENGINE_ID = os.getenv("CUSTOM_SEARCH_ENGINE_ID")
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY") # Optional, if Perplexity features are re-enabled

# Gemini Model Names
GEMINI_FLASH_MODEL = os.getenv("GEMINI_FLASH_MODEL", 'gemini-2.5-flash-preview-05-20') 
GEMINI_SUMMARY_MODEL = os.getenv("GEMINI_SUMMARY_MODEL", 'gemini-2.5-flash-preview-05-20')
# User mentioned 'gemini-2.0-flash', allow override via .env if they have access to such a model
# Otherwise, default to a known public model.
# Max characters of article text to send to Gemini Flash for verification tasks.
# Flash models (e.g., gemini-1.5-flash-latest) can handle large contexts (e.g., up to 1M tokens).
# We set a practical limit here; 150,000 chars is roughly ~30-50k tokens.
# This value is used in article_handler.py to truncate text sent for verification.
GEMINI_FLASH_MODEL_CONTEXT_LIMIT_CHARS = int(os.getenv("GEMINI_FLASH_MODEL_CONTEXT_LIMIT_CHARS", "150000"))
# Max characters of article text to send to the Gemini model used for English summarization.
GEMINI_SUMMARY_MODEL_CONTEXT_LIMIT_CHARS = int(os.getenv("GEMINI_SUMMARY_MODEL_CONTEXT_LIMIT_CHARS", "150000"))

# Perplexity API Configuration (Optional - if used)
PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"
PERPLEXITY_SEARCH_MODEL = os.getenv("PERPLEXITY_SEARCH_MODEL", "sonar-pro") 

# News Discovery Configuration
TARGET_NEWS_SOURCES_DOMAINS = [
    "nyunews.com", 
    "www.nyu.edu/news"
]
CATEGORY_PAGES_TO_SCAN = [
    "https://nyunews.com/category/news/"
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
    if not GOOGLE_API_KEY:
        errors.append("GOOGLE_API_KEY is not set (for Custom Search).")
    if not CUSTOM_SEARCH_ENGINE_ID:
        errors.append("CUSTOM_SEARCH_ENGINE_ID (CX ID) is not set (for Custom Search).")

    if errors:
        error_message = "Configuration errors found:\n" + "\n".join(errors) + \
                        f"\nPlease ensure your .env file is correctly set up at: {DOTENV_PATH}"
        raise ValueError(error_message)
    
    # Corrected f-string for status message
    dotenv_status_message = f"successfully from {DOTENV_PATH}" if os.path.exists(DOTENV_PATH) else "from environment variables (or .env not found/readable)"
    print(f"Configuration loaded {dotenv_status_message}.")
    print(f"  GEMINI_FLASH_MODEL: {GEMINI_FLASH_MODEL}")
    print(f"  GEMINI_SUMMARY_MODEL: {GEMINI_SUMMARY_MODEL}")
    print(f"  Output directory: {DEFAULT_OUTPUT_DIR}")

if not all([GEMINI_API_KEY, GOOGLE_API_KEY, CUSTOM_SEARCH_ENGINE_ID]):
    if os.path.exists(DOTENV_PATH):
        print(f"Warning: Attempted to load .env from {DOTENV_PATH}, but one or more critical API keys (GEMINI, GOOGLE_API_KEY, CUSTOM_SEARCH_ENGINE_ID) are still missing from the environment.")
    else:
        print(f"Warning: .env file not found at {DOTENV_PATH}. One or more critical API keys (GEMINI, GOOGLE_API_KEY, CUSTOM_SEARCH_ENGINE_ID) might be missing.") 