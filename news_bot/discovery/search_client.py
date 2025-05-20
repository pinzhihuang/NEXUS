# news_bot/discovery/search_client.py

import requests
import json
import re
import os
from datetime import date, timedelta
from ..core import config

def find_relevant_articles() -> list[dict[str, str]]:
    """
    Queries the Perplexity API (using sonar-pro or sonar) to find news articles.
    Returns a list of dictionaries, where each dictionary contains 'url' and 'title' (title might be N/A).
    """
    if not config.PERPLEXITY_API_KEY:
        print("Error: PERPLEXITY_API_KEY not configured.")
        return []

    today = date.today()
    search_since_date = (today - config.RECENCY_TIMEDELTA).strftime('%Y-%m-%d')
    
    # === TEMPORARY TEST: Simplify keywords and domains ===
    # Original keywords logic:
    # keywords_for_query = " OR ".join([f'"{k.strip()}"' for k in config.RELEVANCE_KEYWORDS if k.strip()])
    # Original domains logic:
    # domains_list = config.TARGET_NEWS_SOURCES_DOMAINS
    # domains_str = ", ".join(domains_list)

    # TEST VALUES:
    test_domain = "nyunews.com" # Test with one specific domain
    test_keywords = "NYU student life" # Test with a very broad keyword
    print(f"*** RUNNING WITH TEMPORARY TEST DOMAIN: {test_domain} AND KEYWORDS: {test_keywords} ***")
    domains_list = [test_domain] # For URL validation later
    # === END TEMPORARY TEST ===

    system_prompt = (
        "You are an AI assistant. Your task is to find and list URLs of recent news articles from a specific website based on the user's query. "
        "Provide ONLY the information requested, in the exact format specified. Do not add any other text."
    )
    
    # User prompt: Extremely simplified for testing sonar-pro's basic site search capability
    user_prompt = f"""List direct URLs for any news articles published on or after {search_since_date} from the website {test_domain} that are about '{test_keywords}'.

If you find relevant articles, list ONLY their direct URLs, one URL per line.
Example of expected output if articles are found:
https://www.example.com/article1
https://www.example.com/another-article

If NO relevant articles are found, your entire response must be ONLY the phrase: 'No relevant articles found.'
"""

    headers = {
        "Authorization": f"Bearer {config.PERPLEXITY_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    perplexity_model_to_use = config.PERPLEXITY_SEARCH_MODEL 

    payload = {
        "model": perplexity_model_to_use, 
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "max_tokens": 1500, 
        "temperature": 0.0 
    }

    print(f"Sending search request to Perplexity API (Model: {perplexity_model_to_use})...")
    print(f"TESTING with Domain: {test_domain}, Keywords: '{test_keywords}', Since: {search_since_date}")
    # print(f"Full User Prompt for Perplexity:\n{user_prompt}") # For debugging full prompt

    found_articles = []
    try:
        response = requests.post(config.PERPLEXITY_API_URL, headers=headers, json=payload, timeout=90)
        response.raise_for_status()
        result = response.json()

        if not result.get("choices") or not result["choices"][0].get("message"):            
            print("Error: Perplexity API response is not in the expected format or is empty.")
            print(f"Raw response: {result}")
            return []
            
        content = result["choices"][0]["message"]["content"].strip()
        print(f"Perplexity API Content Received:\n---\n{content}\n---")

        if content == "No relevant articles found." or not content.strip():
            print("Perplexity API reported no relevant articles found or returned empty content.")
            return []

        urls = content.splitlines()
        for raw_url in urls:
            url = raw_url.strip()
            # Basic URL validation and domain check (using the test_domain for this specific test)
            if url.startswith("http") and (test_domain in url): # Ensure it's from the test domain
                found_articles.append({"title": "N/A (fetch later)", "url": url})
                if len(found_articles) >= config.MAX_SEARCH_RESULTS_TO_PROCESS:
                    break
            elif url: 
                print(f"Skipping line from Perplexity (not a valid/matching URL or empty): '{url}'")
        
        if not found_articles and content:
             print("Warning: Content received from Perplexity, but no valid URLs could be parsed or matched domain/format criteria FOR THE TEST.")

        print(f"Successfully parsed {len(found_articles)} URLs from Perplexity API (TEST RUN).")

    except requests.exceptions.RequestException as e:
        print(f"Error querying Perplexity API: {e}")
    except json.JSONDecodeError:
        print("Error: Could not decode JSON response from Perplexity API.")
    except Exception as e:
        print(f"An unexpected error occurred in find_relevant_articles: {e}")

    return found_articles

if __name__ == '__main__':
    print("Testing Perplexity search client (EXTREMELY simplified TEMPORARY prompt for sonar-pro)...")
    import sys
    if '..'.join(os.path.abspath(__file__).split(os.sep)[:-2]) not in sys.path:
         sys.path.insert(0, '..'.join(os.path.abspath(__file__).split(os.sep)[:-2]))
    from news_bot.core import config 
    config.validate_config()
    articles = find_relevant_articles()
    if articles:
        print("\nFound article URLs (TEST RUN):")
        for i, article in enumerate(articles):
            print(f"{i+1}. URL: {article['url']}")
    else:
        print("No article URLs found or an error occurred (TEST RUN).") 