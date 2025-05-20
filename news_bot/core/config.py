# news_bot/core/config.py

import os
from dotenv import load_dotenv
from datetime import timedelta

# Load environment variables from .env file in the project root
# Assuming .env is in the parent directory of 'news_bot' (i.e., project root)
DOTENV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), '.env')
load_dotenv(DOTENV_PATH)

# API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
CUSTOM_SEARCH_ENGINE_ID = os.getenv("CUSTOM_SEARCH_ENGINE_ID")

# Gemini Model Names
# Using 'latest' is generally good for getting recent updates.
# For "Gemini 2.0 Flash", 'gemini-1.5-flash-latest' is a strong candidate.
# For summarization, a more powerful model like Pro might be better if quality is paramount.
GEMINI_FLASH_MODEL = 'gemini-2.0-flash' 
# GEMINI_SUMMARY_MODEL = 'gemini-1.5-pro-latest' # Example if you want a different model for summaries
GEMINI_SUMMARY_MODEL = 'gemini-2.0-flash' # Sticking with Flash for consistency for now


# Perplexity API Configuration (might be deprecated if fully switching to Google PSE)
PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"
# Model used for Perplexity search - this might need tuning based on API capabilities
# sonar-small-online might be faster/cheaper for search if available and suitable
# sonar-medium-online (previously sonar-deep-research)
PERPLEXITY_SEARCH_MODEL = "sonar-pro" # User confirmed sonar-pro, adjust as per actual availability

# Google Programmable Search Engine Configuration
# No specific URL needed here, API client handles it.

# News Discovery Configuration
# TARGET_NEWS_SOURCES_DOMAINS is primarily for PSE setup now, but can be used for URL validation
# Removing nytimes.com as per user request due to consistent 403 errors
TARGET_NEWS_SOURCES_DOMAINS = [
    # "nytimes.com", # Removed
    "nyunews.com", # WSN main domain
    "www.nyu.edu/news"
]
# A more precise list for NYU official news if known:
# TARGET_NYU_SITES = ["www.nyu.edu/news", "as.nyu.edu/journalism/news.html", etc.]

# Specific category pages to scan directly for article links
CATEGORY_PAGES_TO_SCAN = [
    "https://nyunews.com/category/news/"
]

RELEVANCE_KEYWORDS = [
    "Chinese international students", "NYU News","New York student life", "NYU campus events"
]

# Article Verification Configuration
RECENCY_THRESHOLD_DAYS = 7 # Default, can be overridden for testing
RECENCY_TIMEDELTA = timedelta(days=RECENCY_THRESHOLD_DAYS)

# Output Configuration
DEFAULT_OUTPUT_DIR = "news_reports"
MAX_FINAL_REPORTS = 5 # Max number of news items in the final report

# Error Handling & Logging
# MAX_SEARCH_RESULTS_TO_PROCESS is now more about how many Google PSE results we check
MAX_SEARCH_RESULTS_TO_PROCESS = 10 # Limit number of search results to avoid excessive API calls
URL_FETCH_TIMEOUT = 20 # seconds

def validate_config():
    """Validates that essential configurations are set."""
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not set in the .env file or environment.")
    if not GOOGLE_API_KEY: # Assuming Google PSE is the primary search now
        raise ValueError("GOOGLE_API_KEY is not set for Custom Search.")
    if not CUSTOM_SEARCH_ENGINE_ID:
        raise ValueError("CUSTOM_SEARCH_ENGINE_ID (CX ID) is not set for Custom Search.")
    # Perplexity key check can be made optional if not used
    # if not PERPLEXITY_API_KEY:
    #     print("Warning: PERPLEXITY_API_KEY is not set. Perplexity-based search will fail.")
    print("Configuration loaded. Essential API keys appear to be present.")

# You might call validate_config() here to check on import,
# or call it explicitly at the start of main_orchestrator.py
# For now, let's print a message if keys are missing when this module is loaded.
if not GEMINI_API_KEY or not GOOGLE_API_KEY or not CUSTOM_SEARCH_ENGINE_ID:
    print("Warning: One or more critical API keys (GEMINI, GOOGLE_API_KEY, CUSTOM_SEARCH_ENGINE_ID) are missing.")
    print(f"Attempted to load .env from: {DOTENV_PATH}") 