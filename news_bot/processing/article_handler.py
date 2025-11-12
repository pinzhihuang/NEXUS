# news_bot/processing/article_handler.py

import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
from datetime import datetime, date, timedelta
import json
import re # For URL date parsing
from ..discovery.date_extractor import extract_date_from_url
from ..utils import prompt_logger

from ..core import config

def fetch_and_extract_text(url: str) -> str | None:
    """
    Fetches content from a URL and extracts clean textual content.
    """
    print(f"Fetching and extracting text from: {url}")
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=config.URL_FETCH_TIMEOUT)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        # if read full button found, extract the text from button's url (apply to UBC)
        try:
            read_full_button = soup.find('a', text='Read the full message')
            if read_full_button:
                url = read_full_button['href']
                print(f"DEBUG: read full button found, url: {url}\n")
                response = requests.get(url, headers=headers, timeout=config.URL_FETCH_TIMEOUT)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
        except Exception as e:
            print(f"not read full button found")
            pass
        
        # --- Domain-specific extraction: The Student News (avoid hidden trending preview article) ---
        article_body = None
        try:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc
        except Exception:
            domain = ''

        if 'thestudentnews.co.uk' in domain:
            # Prefer the real article content container inside the primary content area
            tsn_selectors = [
                '#content #primary article .entry-content',
                '#primary .entry-content',
                'main.site-main article .entry-content',
                '.single-post .entry-content',
                '.entry-content'
            ]
            for css in tsn_selectors:
                el = soup.select_one(css)
                if el:
                    article_body = el
                    print(f"DEBUG: thestudentnews extractor using selector: '{css}'")
                    break

        # --- Generic extraction (ordered: specific containers first, 'article' last) ---
        if not article_body:
            main_content_tags = ['.entry-content', '.post-content', '.td-post-content', 'main', 'article']
            for tag_or_class in main_content_tags:
                if tag_or_class.startswith('.'):
                    article_body = soup.find(class_=tag_or_class[1:])
                else:
                    article_body = soup.find(tag_or_class)
                if article_body:
                    print(f"DEBUG: article_body found via generic selector '{tag_or_class}', url: {url}")
                    break
        
        if not article_body:
            article_body = soup.body

        text_content = ""
        if article_body:
            for unwanted_tag in article_body(['script', 'style', 'nav', 'footer', 'aside', 'header', 'form', 'button', 'input', 'textarea', 'select', 'option']):
                unwanted_tag.decompose()
            
            common_annoyances_selectors = [
                '[class*="mask"]',
                '[class*="ad"], [id*="ad"]' ,
                '[class*="popup"], [id*="popup"]' ,
                '[class*="overlay"], [id*="overlay"]' ,
                '[class*="banner"], [id*="banner"]' ,
                '[class*="cookie"], [id*="cookie"]',
                '[class*="share"], [id*="share"]' # Share buttons/widgets
            ]
            for selector in common_annoyances_selectors:
                for unwanted_element in article_body.select(selector):
                    unwanted_element.decompose()

            paragraphs = article_body.find_all('p')
            # print(f"DEBUG: paragraphs: {paragraphs}\n")
            if paragraphs:
                text_content = "\n".join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
            
            if not text_content or len(text_content.split()) < 30: # Slightly lower threshold
                alternative_text = article_body.get_text(separator='\n', strip=True)
                if len(alternative_text.split()) > len(text_content.split()):
                    text_content = alternative_text
        
        if not text_content.strip():
             print(f"Info: No significant text content from primary containers of {url}. Trying full soup minus known non-content tags.")
             for unwanted_tag in soup(['script', 'style', 'nav', 'footer', 'aside', 'header', 'form', 'button', 'input', 'textarea', 'select', 'option']):
                unwanted_tag.decompose()
             text_content = soup.get_text(separator='\n', strip=True)

        if not text_content.strip():
            print(f"Warning: Still no significant text content extracted from {url}.")
            return None

        cleaned_text = "\n".join([line for line in text_content.splitlines() if line.strip()])
        print(f"Successfully extracted text from {url} (approx. {len(cleaned_text.split())} words).")
        return cleaned_text

    except requests.exceptions.Timeout:
        print(f"Error: Timeout while fetching URL {url}")
    except requests.exceptions.HTTPError as e:
        print(f"Error: HTTP error {e.response.status_code} while fetching URL {url}")
    except requests.exceptions.RequestException as e:
        print(f"Error: Could not fetch URL {url}. Details: {str(e)}")
    except Exception as e:
        print(f"Error: An unexpected error occurred while fetching/processing URL {url}: {str(e)}")
    return None


def verify_article_with_gemini(school: dict[str, str], article_text: str, article_url: str, publication_date: str) -> dict | None:
    """
    Verifies an article using Gemini for date extraction and article type assessment.
    Relevance is already filtered in Step 1, so this step focuses on date accuracy and article classification.
    Uses the configured date range from config.get_news_date_range().
    Supplements Gemini date extraction with URL parsing if Gemini fails.
    Uses Gemini 2.5 Pro for better accuracy.
    """
    if not config.GEMINI_API_KEY:
        print("Error: GEMINI_API_KEY not configured for verification.")
        return None
    
    # Get the configured date range
    start_date, end_date = config.get_news_date_range()
    
    if not article_text or not article_text.strip():
        print(f"Info: Skipping Gemini verification for {article_url} due to empty article text.")
        publication_date_from_url = publication_date
        final_date_str = publication_date_from_url if publication_date_from_url else "Date not found"
        is_recent_status = "Date unclear (no text/URL date)"
        is_within_range = False
        
        if publication_date_from_url:
            try:
                pub_dt = datetime.strptime(publication_date_from_url, "%Y-%m-%d").date()
                if pub_dt >= start_date and pub_dt <= end_date:
                    is_recent_status = f"Within range (from URL, {start_date} to {end_date})"
                    is_within_range = True
                elif pub_dt > end_date:
                    is_recent_status = f"After range (from URL, after {end_date})"
                else:
                    is_recent_status = f"Before range (from URL, before {start_date})"
            except ValueError:
                is_recent_status = "Date unparsable (from URL)"
        
        return {
            "url": article_url,
            "publication_date_str": final_date_str,
            "is_recent": is_recent_status,
            "is_within_range": is_within_range,
            "is_relevant": "Relevant",  # Already filtered in Step 1
            "article_type_assessment": "Type unclear (no text)"
        }

    print(f"Verifying article with Gemini: {article_url[:100]}...")
    print(f"Using date range: {start_date} to {end_date}")
    
    try:
        genai.configure(api_key=config.GEMINI_API_KEY)
        model = genai.GenerativeModel(config.GEMINI_PRO_MODEL)
    except Exception as e:
        print(f"Error initializing Gemini model for verification: {str(e)}")
        return None

    context_limit = getattr(config, 'GEMINI_PRO_MODEL_CONTEXT_LIMIT_CHARS', 2000000)
    article_text_limit = min(len(article_text), context_limit // 2)  # Use half for safety
    
    prompt = f"""You are a news article analyst. Your task is to extract key metadata from the article text.

## Requirements

### Accuracy & Factuality (Highest Priority)
- Extract dates ONLY from the article text or URL - do not infer or guess dates
- Base article type classification strictly on the content structure and purpose
- Do not add information not present in the article

### Task
Analyze the article and provide your analysis in EXACTLY three lines, each starting with the specified prefix:

1. Publication Date: [Review the article text AND the Article URL ({article_url}). Extract the most prominent date, ideally the publication date. Format YYYY-MM-DD or 'Date not found'. No other explanation.]
2. Article Type: [Is this primarily a news article reporting on events/facts, or an opinion/blog/event listing/announcement? Answer ONLY 'News article', 'Opinion/Blog', 'Event/Announcement', or 'Type unclear'. No other explanation.]
3. Analysis Notes: [Brief internal notes if needed, or 'N/A'. This line is for your process.]

## Input Data

--- Article Text (first {article_text_limit} characters) ---
{article_text[:article_text_limit]}
--- End of Article Text ---

Your response (exactly 3 lines as specified above):
""" 

    gemini_publication_date_str = "Date not found" # Default from Gemini
    try:
        print(f"Sending verification request to Gemini API ({config.GEMINI_PRO_MODEL})...")
        
        # Log the prompt
        prompt_logger.log_prompt(
            "verify_article_with_gemini",
            prompt,
            context={
                "article_url": article_url,
                "publication_date": publication_date,
                "school": school.get('school_name', 'Unknown'),
                "article_text_length": len(article_text)
            }
        )
        
        response = model.generate_content(prompt)
        raw_response_text = getattr(response, 'text', '').strip()
        if not raw_response_text and hasattr(response, 'parts') and response.parts:
            for part in response.parts:
                raw_response_text += getattr(part, 'text', '').strip()
            raw_response_text = raw_response_text.strip()

        if not raw_response_text:
            print(f"Error: Empty response from Gemini verification for {article_url}.")
            # Proceed with URL date parsing as fallback
            final_article_type = "Type unclear (empty response)"
        else:
            print(f"Gemini Verification Raw Response for {article_url[:100]}...:\n---\n{raw_response_text}\n---")
            lines = raw_response_text.split('\n')
            # Initialize with defaults that indicate Gemini didn't provide this specific field
            results_from_gemini = {
                "publication_date_str": "Date not found by Gemini",
                "article_type_assessment": "Type unclear (Gemini parsing error)"
            }
            parsed_items_count = 0
            for line_idx, line in enumerate(lines[:3]): # Only process up to the first 3 expected lines
                line_strip = line.strip()
                if (line_idx == 0 and "Publication Date:" in line_strip) or (not results_from_gemini["publication_date_str"] == "Date not found by Gemini" and "Publication Date:" in line_strip):
                    results_from_gemini["publication_date_str"] = line_strip.split("Publication Date:", 1)[-1].strip()
                    parsed_items_count += 1
                elif (line_idx == 1 and "Article Type:" in line_strip) or (results_from_gemini["article_type_assessment"] == "Type unclear (Gemini parsing error)" and "Article Type:" in line_strip):
                    results_from_gemini["article_type_assessment"] = line_strip.split("Article Type:", 1)[-1].strip()
                    parsed_items_count += 1
            
            gemini_publication_date_str = results_from_gemini["publication_date_str"]
            final_article_type = results_from_gemini["article_type_assessment"]

            if parsed_items_count < 2:
                print(f"Warning: Gemini verification response for {article_url} did not parse all expected fields. Parsed: {parsed_items_count}/2.")

    except Exception as e_gemini:
        print(f"Error during Gemini API call or parsing for verification of {article_url}: {e_gemini}")
        # Defaults will be used, attempt URL date parsing
        final_article_type = "Type unclear (Gemini API error)"

    # Determine final date string (Gemini > URL > Not found)
    final_date_str = gemini_publication_date_str
    date_source_log = "(from Gemini)"
    if final_date_str.lower() == "date not found" or "error" in final_date_str.lower() or not final_date_str.strip():
        print(f"Info: Gemini did not find date for {article_url}. Attempting URL parse.")
        url_extracted_date = publication_date
        if url_extracted_date:
            final_date_str = url_extracted_date
            date_source_log = "(from URL)"
            print(f"Info: Extracted date {final_date_str} from URL for {article_url}.")
        else:
            final_date_str = "Date not found"
            date_source_log = "(no date found)"

    # Determine recency based on the final_date_str and configured date range
    is_recent_status = "Date unclear"
    is_within_range = False  # Track if date is actually within range
    
    if final_date_str.lower() == "date not found" or "error" in final_date_str.lower():
        is_recent_status = f"Date unclear {date_source_log}"
    else:
        try:
            publication_date_dt = datetime.strptime(final_date_str, "%Y-%m-%d").date()
            if publication_date_dt >= start_date and publication_date_dt <= end_date:
                is_recent_status = f"Within range {date_source_log} ({start_date} to {end_date})"
                is_within_range = True
            elif publication_date_dt > end_date:
                is_recent_status = f"After range {date_source_log} (after {end_date})"
            else:
                is_recent_status = f"Before range {date_source_log} (before {start_date})"
        except ValueError:
            is_recent_status = f"Date unparsable {date_source_log}"
            print(f"Warning: Could not parse final date '{final_date_str}' for {article_url}.")
        
    final_results = {
        "url": article_url,
        "publication_date_str": final_date_str,
        "is_recent": is_recent_status,
        "is_within_range": is_within_range,
        "is_relevant": "Relevant",  # Already filtered in Step 1, so assume relevant
        "article_type_assessment": final_article_type if 'final_article_type' in locals() else "Type unclear (init error)"
    }
    print(f"Verification results for {article_url[:100]}...: {final_results}")
    return final_results

if __name__ == '__main__':
    print("Testing Article Handler...")
    import sys
    import os
    PROJECT_ROOT_FOR_TEST = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if PROJECT_ROOT_FOR_TEST not in sys.path:
         sys.path.insert(0, PROJECT_ROOT_FOR_TEST)
    
    from news_bot.core import config
    config.validate_config()
    # Add a placeholder for GEMINI_FLASH_MODEL_CONTEXT_LIMIT_CHARS if not in config for testing
    if not hasattr(config, 'GEMINI_FLASH_MODEL_CONTEXT_LIMIT_CHARS'):
        print("Warning: GEMINI_FLASH_MODEL_CONTEXT_LIMIT_CHARS not in config, defaulting to 100000 for test.")
        config.GEMINI_FLASH_MODEL_CONTEXT_LIMIT_CHARS = 100000 

    # Test URL with date in it
    test_url_wsn_with_date = "https://nyunews.com/news/2024/05/16/gallatin-student-speaker-diploma-withheld/"
    # Test URL likely without clear date in URL, relying on Gemini or byline (if fetched)
    test_url_nyu_no_clear_url_date = "https://www.nyu.edu/about/news-publications/news/2024/march/nyu-appoints-deans-for-arts-and-science-and-global-public-heal.html"
    # Test with a non-article page that might have a date-like structure in URL
    test_url_category_like = "https://nyunews.com/category/news/2023/"

    urls_to_test = [test_url_wsn_with_date, test_url_nyu_no_clear_url_date, test_url_category_like]

    for i, test_url in enumerate(urls_to_test):
        print(f"\n--- Test {i+1}: Processing URL: {test_url} ---")
        
        # Test URL date extraction directly
        # extracted_date = extract_date_from_url(test_url) # Not used in this test
        print(f"  Direct URL date extraction attempt: {extracted_date}")

        article_text = fetch_and_extract_text(test_url)
        if not article_text and "category" in test_url: # For category pages, text extraction might be minimal
            print("  Minimal or no text expected from category page, using placeholder for verification test.")
            article_text = "This is a category page listing many articles about NYU events." 
        
        if article_text:
            verification_results = verify_article_with_gemini(article_text, test_url)
            if verification_results:
                print(f"Verification Results for {test_url}:\n{json.dumps(verification_results, indent=2)}")
            else:
                print(f"Failed to get verification results for {test_url}.")
        else:
            print(f"Failed to fetch or extract text from {test_url} (and not a category page for test text). Skipping verification.")