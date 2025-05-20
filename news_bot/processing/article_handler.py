# news_bot/processing/article_handler.py

import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
from datetime import datetime, date
import json

from ..core import config # For API keys, model names, timeouts, etc.

def fetch_and_extract_text(url: str) -> str | None:
    """
    Fetches content from a URL and extracts clean textual content using BeautifulSoup.

    Args:
        url: The URL of the article to fetch.

    Returns:
        The extracted text content as a string, or None if fetching/parsing fails.
    """
    print(f"Fetching and extracting text from: {url}")
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=config.URL_FETCH_TIMEOUT)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Try to find common main content containers
        main_content_tags = ['article', 'main', '.post-content', '.entry-content', '.td-post-content'] # Common class names
        article_body = None
        for tag_or_class in main_content_tags:
            if tag_or_class.startswith('.'): # It's a class
                article_body = soup.find(class_=tag_or_class[1:]) # Remove leading dot
            else: # It's a tag
                article_body = soup.find(tag_or_class)
            if article_body:
                break # Found a container
        
        if not article_body:
            # Fallback to body if no specific main content tag is found
            article_body = soup.body

        text_content = ""
        if article_body:
            # Remove common non-content elements like scripts, styles, nav, footers, ads, popups, sidebars
            for unwanted_tag in article_body(['script', 'style', 'nav', 'footer', 'aside', 'header', 'form']): # Added 'header' and 'form'
                unwanted_tag.decompose()
            
            # Selectors for common ad/popup/overlay classes/ids (can be expanded)
            common_annoyances_selectors = [
                '[class*="ad"], [id*="ad"]' ,
                '[class*="popup"], [id*="popup"]' ,
                '[class*="overlay"], [id*="overlay"]' ,
                '[class*="banner"], [id*="banner"]' ,
                '[class*="cookie"], [id*="cookie"]' # Cookie consent bars
            ]
            for selector in common_annoyances_selectors:
                for unwanted_element in article_body.select(selector):
                    unwanted_element.decompose()

            # Get text from paragraphs first, then broader text if needed
            paragraphs = article_body.find_all('p')
            if paragraphs:
                text_content = "\n".join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
            
            # If paragraph extraction yields little, try a more general text extraction from the container
            if not text_content or len(text_content.split()) < 50: # Arbitrary threshold for too little content
                alternative_text = article_body.get_text(separator='\n', strip=True)
                if len(alternative_text.split()) > len(text_content.split()):
                    text_content = alternative_text
        
        if not text_content.strip(): # If still nothing, try from the whole soup as last resort
             print(f"Warning: No significant text content extracted from primary containers of {url}. Trying full soup.")
             for unwanted_tag in soup(['script', 'style', 'nav', 'footer', 'aside', 'header', 'form']):
                unwanted_tag.decompose()
             text_content = soup.get_text(separator='\n', strip=True)

        if not text_content.strip():
            print(f"Warning: Still no significant text content extracted from {url} after all attempts.")
            return None # Return None if truly empty

        print(f"Successfully extracted text from {url} (approx. {len(text_content.split())} words).")
        return "\n".join([line for line in text_content.splitlines() if line.strip()]) # Clean up empty lines

    except requests.exceptions.Timeout:
        print(f"Error: Timeout while fetching URL {url}")
    except requests.exceptions.HTTPError as e:
        print(f"Error: HTTP error {e.response.status_code} while fetching URL {url}")
    except requests.exceptions.RequestException as e:
        print(f"Error: Could not fetch URL {url}. {str(e)}")
    except Exception as e:
        print(f"Error: An unexpected error occurred while processing URL {url}: {str(e)}")
        # import traceback
        # traceback.print_exc()
    return None

def verify_article_with_gemini(article_text: str, article_url: str) -> dict | None:
    """
    Verifies an article using Gemini for date, recency, relevance, and article type.
    Returns a dictionary with keys: url, publication_date_str, is_recent, is_relevant, article_type_assessment.
    """
    if not config.GEMINI_API_KEY:
        print("Error: GEMINI_API_KEY not configured for verification.")
        return None
    if not article_text or not article_text.strip():
        print(f"Skipping Gemini verification for {article_url} due to empty article text.")
        return {
            "url": article_url,
            "publication_date_str": "Date not found",
            "is_recent": "Date unclear",
            "is_relevant": "Relevance unclear (no text)",
            "article_type_assessment": "Type unclear (no text)" # Changed from appears_factual
        }

    print(f"Verifying article with Gemini: {article_url}")
    try:
        genai.configure(api_key=config.GEMINI_API_KEY)
        model = genai.GenerativeModel(config.GEMINI_FLASH_MODEL)
    except Exception as e:
        print(f"Error initializing Gemini model for verification: {str(e)}")
        return None

    today = date.today()
    relevance_query = f"Is this article relevant to Chinese international students at NYU (studies, work, daily life, immigration, campus events, US-China relations affecting students)? URL: {article_url}"
    
    prompt = f"""Analyze the article text. Provide your analysis in EXACTLY four lines, each starting with the specified prefix:

1. Publication Date: [Extract the most prominent date, ideally publication date. Format YYYY-MM-DD or 'Date not found'. No other explanation.]
2. Relevance: [Based on the text and this query: '{relevance_query}', answer ONLY 'Relevant', 'Not relevant', or 'Relevance unclear'. No other explanation.]
3. Article Type: [Is this primarily a news article reporting on events/facts, or an opinion/blog/event listing/announcement? Answer ONLY 'News article', 'Opinion/Blog', 'Event/Announcement', or 'Type unclear'. No other explanation.]
4. Analysis Notes: [Brief internal notes if needed, or 'N/A'. This line is for your process.]

--- Article Text (first 100,000 characters) ---
{article_text[:100000]}
--- End of Article Text ---

Your response (exactly 4 lines as specified above):
"""

    # print(f"Gemini Verification Prompt (first 500 chars):\n{prompt[:500]}...") # For debugging

    try:
        print(f"Sending verification request to Gemini API ({config.GEMINI_FLASH_MODEL})...")
        response = model.generate_content(prompt)
        
        raw_response_text = ""
        if hasattr(response, 'text'):
            raw_response_text = response.text.strip()
        elif hasattr(response, 'parts') and response.parts:
            for part in response.parts:
                if hasattr(part, 'text'):
                    raw_response_text += part.text.strip()
            raw_response_text = raw_response_text.strip()
        else:
            print(f"Error: Gemini verification response for {article_url} in unexpected format.")
            return None

        if not raw_response_text:
            print(f"Error: Empty response from Gemini verification for {article_url}.")
            return None
            
        print(f"Gemini Verification Raw Response for {article_url}:\n---\n{raw_response_text}\n---")

        lines = raw_response_text.split('\n')
        results = {
            "url": article_url,
            "publication_date_str": "Date extraction error",
            "is_relevant": "Relevance unclear (parsing error)",
            "article_type_assessment": "Type unclear (parsing error)", # Changed key
            "is_recent": "Date unclear (parsing error)" 
        }

        parsed_items_count = 0
        for line in lines:
            line_strip = line.strip()
            if "Publication Date:" in line_strip:
                results["publication_date_str"] = line_strip.split("Publication Date:", 1)[-1].strip()
                parsed_items_count += 1
            elif "Relevance:" in line_strip:
                results["is_relevant"] = line_strip.split("Relevance:", 1)[-1].strip()
                parsed_items_count += 1
            elif "Article Type:" in line_strip: # Changed keyword to match prompt
                results["article_type_assessment"] = line_strip.split("Article Type:", 1)[-1].strip()
                parsed_items_count += 1

        if parsed_items_count < 3:
            print(f"Warning: Gemini verification response for {article_url} did not parse all expected fields (date, relevance, type). Parsed: {parsed_items_count}/3.")

        date_str = results["publication_date_str"]
        if date_str.lower() == "date not found" or "error" in date_str.lower():
            results["is_recent"] = "Date unclear"
        else:
            try:
                publication_date_dt = datetime.strptime(date_str, "%Y-%m-%d").date()
                if (today - publication_date_dt) <= config.RECENCY_TIMEDELTA and publication_date_dt <= today:
                    results["is_recent"] = "Recent"
                elif publication_date_dt > today:
                    results["is_recent"] = "Date in future"
                else:
                    results["is_recent"] = "Not recent"
            except ValueError:
                results["is_recent"] = "Date unparsable"
                print(f"Warning: Could not parse date '{date_str}' from Gemini for {article_url}.")
        
        print(f"Verification results for {article_url}: {results}")
        return results

    except Exception as e:
        print(f"Error during Gemini API call for verification of {article_url}: {e}")
        # import traceback
        # traceback.print_exc()
        return None

if __name__ == '__main__':
    # This is for testing the module directly
    print("Testing Article Handler...")
    # Ensure your .env file is in the project root for this to work when run directly
    # (Path adjustments similar to search_client.py might be needed if run standalone)
    import sys
    import os
    if '..'.join(os.path.abspath(__file__).split(os.sep)[:-2]) not in sys.path:
         sys.path.insert(0, '..'.join(os.path.abspath(__file__).split(os.sep)[:-2]))
    
    from news_bot.core import config # Re-import
    config.validate_config() # Check API keys

    test_url_valid = "https://www.nyu.edu/about/news-publications/news/2024/march/nyu-appoints-deans-for-arts-and-science-and-global-public-heal.html" # A real NYU news page
    test_url_general_news = "https://www.nytimes.com/2024/05/20/us/politics/biden-commencement-speech-morehouse.html" # A real NYT article
    test_url_wsn = "https://nyunews.com/news/2024/05/16/gallatin-student-speaker-diploma-withheld/" # WSN article

    urls_to_test = [test_url_valid, test_url_general_news, test_url_wsn]

    for i, test_url in enumerate(urls_to_test):
        print(f"\n--- Test {i+1}: Processing URL: {test_url} ---")
        article_text = fetch_and_extract_text(test_url)
        if article_text:
            print(f"Extracted text (first 300 chars):\n{article_text[:300]}...")
            verification_results = verify_article_with_gemini(article_text, test_url)
            if verification_results:
                print(f"Verification Results for {test_url}:\n{json.dumps(verification_results, indent=2)}")
            else:
                print(f"Failed to get verification results for {test_url}.")
        else:
            print(f"Failed to fetch or extract text from {test_url}.") 