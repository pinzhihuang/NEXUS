import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

API_KEY = os.getenv("PPLX_API_KEY")
if not API_KEY:
    raise ValueError("Missing API key. Please check your .env file.")

API_URL = "https://api.perplexity.ai/chat/completions"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

TODAY = datetime.today().strftime('%Y-%m-%d')
DISPLAY_DATE = datetime.today().strftime('%Y-%m-%d')
