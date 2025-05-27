# news_bot/processing/article_handler.py

import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
from datetime import datetime, date, timedelta
import json
import re # For URL date parsing
import calendar

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
        
        main_content_tags = ['article', 'main', '.post-content', '.entry-content', '.td-post-content']
        article_body = None
        for tag_or_class in main_content_tags:
            if tag_or_class.startswith('.'):
                article_body = soup.find(class_=tag_or_class[1:])
            else:
                article_body = soup.find(tag_or_class)
            if article_body:
                break
        
        if not article_body:
            article_body = soup.body

        text_content = ""
        if article_body:
            for unwanted_tag in article_body(['script', 'style', 'nav', 'footer', 'aside', 'header', 'form', 'button', 'input', 'textarea', 'select', 'option']):
                unwanted_tag.decompose()
            
            common_annoyances_selectors = [
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
         # --- IMPROVED BYLINE/DATE EXTRACTION ---
        byline_text = ""
        # 1. Try common byline/date classes (including 'publish', 'date')
        byline_candidates = soup.find_all(class_=re.compile(r'byline|dateline|author|publish|date', re.I))
        for byline in byline_candidates:
            byline_text_candidate = byline.get_text(separator=' ', strip=True)
            if byline_text_candidate and len(byline_text_candidate) < 300:
                byline_text += byline_text_candidate + "\n"

        # 2. Fallback: search for any tag containing "Published" and a date in its text
        found_published = False
        for tag in soup.find_all(True):
            tag_text = tag.get_text(separator=' ', strip=True)
            if (
                "Published" in tag_text
                and re.search(r'[A-Za-z]+\s+\d{1,2},\s*\d{4}', tag_text)
                and len(tag_text) < 300
            ):
                byline_text = tag_text + "\n"
                found_published = True
                break  # Only need the first match

        # Prepend byline to the cleaned article text for downstream date extraction
        if byline_text:
            print(f"Byline text extracted for date parsing: {byline_text!r}")
            cleaned_text = byline_text.strip() + "\n" + cleaned_text

        # Prepend byline to the cleaned article text for downstream date extraction
        if byline_text:
            print(f"Byline text extracted for date parsing: {byline_text!r}")  # <-- Add this line
            cleaned_text = byline_text.strip() + "\n" + cleaned_text

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



def _extract_date_from_url(url_string: str) -> str | None:
    """
    Attempts to extract a date (YYYY-MM-DD) from a URL string.
    Looks for patterns like /YYYY/MM/DD/ or /YYYY/MM/.
    """
    
    # Pattern for YYYY/MM/DD
    match_ymd = re.search(r'/(\d{4})/(\d{1,2})/(\d{1,2})/', url_string)
    if match_ymd:
        year, month, day = match_ymd.groups()
        try:
            # Validate if it forms a real date
            dt = datetime(int(year), int(month), int(day))
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass # Invalid date components

    # Pattern for YYYY/MM (default to 01 for day)
    match_ym = re.search(r'/(\d{4})/(\d{1,2})/', url_string)
    if match_ym:
        year, month = match_ym.groups()
        try:
            dt = datetime(int(year), int(month), 1)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass
    
    # Pattern for YYYY-MM-DD directly in a segment
    match_ymd_direct = re.search(r'(\d{4}-\d{1,2}-\d{1,2})', url_string)
    if match_ymd_direct:
        try:
            dt = datetime.strptime(match_ymd_direct.group(1), "%Y-%m-%d")
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass
    
   
            
    return None



def extract_publication_date_from_text(text: str) -> str | None:
    """
    Attempts to extract a publication date from visible article text,
    e.g., 'Published May 16, 2025' or 'Updated on May 16, 2025 at 2:30 pm'.
    Returns date as YYYY-MM-DD if found, else None.
    """
    patterns = [
        r'(?:Published|Updated)(?:\s+on)?(?:\s*•)?\s*([A-Za-z]+)\s+(\d{1,2}),\s*(\d{4})'
    ]
    for pat in patterns:
        match = re.search(pat, text)
        if match:
            month_str, day, year = match.groups()
            try:
                if month_str in calendar.month_name:
                    month_num = list(calendar.month_name).index(month_str)
                elif month_str in calendar.month_abbr:
                    month_num = list(calendar.month_abbr).index(month_str)
                else:
                    continue
                if month_num == 0:
                    continue
                dt = datetime(int(year), int(month_num), int(day))
                return dt.strftime("%Y-%m-%d")
            except Exception:
                continue
    return None

def verify_article_with_gemini(article_text: str, article_url: str) -> dict | None:
    """
    Verifies an article using Gemini for date, recency, relevance, and article type.
    Supplements Gemini date extraction with URL parsing if Gemini fails.
    """
    if not config.GEMINI_API_KEY:
        print("Error: GEMINI_API_KEY not configured for verification.")
        return None
    if not article_text or not article_text.strip():
        print(f"Info: Skipping Gemini verification for {article_url} due to empty article text.")
        publication_date_from_url = _extract_date_from_url(article_url)
        final_date_str = publication_date_from_url if publication_date_from_url else "Date not found"
        is_recent_status = "Date unclear (no text/URL date)"
        if publication_date_from_url:
            try:
                pub_dt = datetime.strptime(publication_date_from_url, "%Y-%m-%d").date()
                today_for_check = date.today()
                oldest_acceptable_date = today_for_check - timedelta(days=config.RECENCY_THRESHOLD_DAYS - 1)
                if pub_dt >= oldest_acceptable_date and pub_dt <= today_for_check:
                    is_recent_status = "Recent (from URL)"
                elif pub_dt > today_for_check:
                    is_recent_status = "Date in future (from URL)"
                else:
                    is_recent_status = "Not recent (from URL)"
            except ValueError:
                is_recent_status = "Date unparsable (from URL)"
        
        return {
            "url": article_url,
            "publication_date_str": final_date_str,
            "is_recent": is_recent_status,
            "is_relevant": "Relevance unclear (no text)",
            "article_type_assessment": "Type unclear (no text)"
        }

    print(f"Verifying article with Gemini: {article_url[:100]}...")
    try:
        genai.configure(api_key=config.GEMINI_API_KEY)
        model = genai.GenerativeModel(config.GEMINI_FLASH_MODEL)
    except Exception as e:
        print(f"Error initializing Gemini model for verification: {str(e)}")
        return None

    today_for_check = date.today()
    relevance_query = f"Is this article generally relevant to students at New York University (NYU), covering campus news, academic updates, student life, or significant events affecting the NYU community?"
    
    prompt = f"""Analyze the article text. Provide your analysis in EXACTLY four lines, each starting with the specified prefix:

1. Publication Date: [Review the article text AND the Article URL ({article_url}). Extract the most prominent date, ideally the publication date. Format YYYY-MM-DD or 'Date not found'. No other explanation.]
2. Relevance: [Based on the text and this query: '{relevance_query}', answer ONLY 'Relevant', 'Not relevant', or 'Relevance unclear'. No other explanation.]
3. Article Type: [Is this primarily a news article reporting on events/facts, or an opinion/blog/event listing/announcement? Answer ONLY 'News article', 'Opinion/Blog', 'Event/Announcement', or 'Type unclear'. No other explanation.]
4. Analysis Notes: [Brief internal notes if needed, or 'N/A'. This line is for your process.]

--- Article Text (first {config.GEMINI_FLASH_MODEL_CONTEXT_LIMIT_CHARS // 2 if hasattr(config, 'GEMINI_FLASH_MODEL_CONTEXT_LIMIT_CHARS') else 50000} characters) ---
{article_text[:config.GEMINI_FLASH_MODEL_CONTEXT_LIMIT_CHARS // 2 if hasattr(config, 'GEMINI_FLASH_MODEL_CONTEXT_LIMIT_CHARS') else 50000]}
--- End of Article Text ---

Your response (exactly 4 lines as specified above):
""" 

    gemini_publication_date_str = "Date not found" # Default from Gemini
    try:
        print(f"Sending verification request to Gemini API ({config.GEMINI_FLASH_MODEL})...")
        response = model.generate_content(prompt)
        raw_response_text = getattr(response, 'text', '').strip()
        if not raw_response_text and hasattr(response, 'parts') and response.parts:
            for part in response.parts:
                raw_response_text += getattr(part, 'text', '').strip()
            raw_response_text = raw_response_text.strip()

        if not raw_response_text:
            print(f"Error: Empty response from Gemini verification for {article_url}.")
            # Proceed with URL date parsing as fallback
        else:
            print(f"Gemini Verification Raw Response for {article_url[:100]}...:\n---\n{raw_response_text}\n---")
            lines = raw_response_text.split('\n')
            # Initialize with defaults that indicate Gemini didn't provide this specific field
            results_from_gemini = {
                "publication_date_str": "Date not found by Gemini",
                "is_relevant": "Relevance unclear (Gemini parsing error)",
                "article_type_assessment": "Type unclear (Gemini parsing error)"
            }
            parsed_items_count = 0
            for line_idx, line in enumerate(lines[:3]): # Only process up to the first 3 expected lines for main data
                line_strip = line.strip()
                if (line_idx == 0 and "Publication Date:" in line_strip) or (not results_from_gemini["publication_date_str"] == "Date not found by Gemini" and "Publication Date:" in line_strip):
                    results_from_gemini["publication_date_str"] = line_strip.split("Publication Date:", 1)[-1].strip()
                    parsed_items_count += 1
                elif (line_idx == 1 and "Relevance:" in line_strip) or (results_from_gemini["is_relevant"] == "Relevance unclear (Gemini parsing error)" and "Relevance:" in line_strip):
                    results_from_gemini["is_relevant"] = line_strip.split("Relevance:", 1)[-1].strip()
                    parsed_items_count += 1
                elif (line_idx == 2 and "Article Type:" in line_strip) or (results_from_gemini["article_type_assessment"] == "Type unclear (Gemini parsing error)" and "Article Type:" in line_strip):
                    results_from_gemini["article_type_assessment"] = line_strip.split("Article Type:", 1)[-1].strip()
                    parsed_items_count += 1
            
            gemini_publication_date_str = results_from_gemini["publication_date_str"]
            final_relevance = results_from_gemini["is_relevant"]
            final_article_type = results_from_gemini["article_type_assessment"]

            if parsed_items_count < 3:
                print(f"Warning: Gemini verification response for {article_url} did not parse all expected fields. Parsed: {parsed_items_count}/3.")

    except Exception as e_gemini:
        print(f"Error during Gemini API call or parsing for verification of {article_url}: {e_gemini}")
        # Defaults will be used, attempt URL date parsing
        final_relevance = "Relevance unclear (Gemini API error)"
        final_article_type = "Type unclear (Gemini API error)"

    # Determine final date string (Gemini > URL > Text > Not found)
    final_date_str = gemini_publication_date_str
    date_source_log = "(from Gemini)"
    if final_date_str.lower() == "date not found" or "error" in final_date_str.lower() or not final_date_str.strip():
        print(f"Info: Gemini did not find date for {article_url}. Attempting URL parse.")
        url_extracted_date = _extract_date_from_url(article_url)
        if url_extracted_date:
            final_date_str = url_extracted_date
            date_source_log = "(from URL)"
            print(f"Info: Extracted date {final_date_str} from URL for {article_url}.")
        else:
            '''
            # Fallback: Try extracting from article text
            text_extracted_date = extract_publication_date_from_text(article_text)
            if text_extracted_date:
                final_date_str = text_extracted_date
                date_source_log = "(from text)"
                print(f"Info: Extracted date {final_date_str} from article text for {article_url}.")
            else:
                final_date_str = "Date not found"
                date_source_log = "(no date found)"
            '''
            
            # After getting gemini_publication_date_str, before determining recency:
            # Try to extract date from article text (byline) if Gemini's date is not in the text
            text_extracted_date = extract_publication_date_from_text(article_text)
            if (
                text_extracted_date
                and (
                    gemini_publication_date_str.lower() == "date not found"
                    or gemini_publication_date_str not in article_text
                    or gemini_publication_date_str != text_extracted_date
                )
            ):
                print(f"Info: Overriding Gemini date '{gemini_publication_date_str}' with extracted date '{text_extracted_date}' from article text for {article_url}.")
                final_date_str = text_extracted_date
                date_source_log = "(from text, override Gemini)"
            else:
                final_date_str = gemini_publication_date_str
                date_source_log = "(from Gemini)"
            


    # Determine recency based on the final_date_str
    is_recent_status = "Date unclear"
    if final_date_str.lower() == "date not found" or "error" in final_date_str.lower():
        is_recent_status = f"Date unclear {date_source_log}"
    else:
        try:
            publication_date_dt = datetime.strptime(final_date_str, "%Y-%m-%d").date()
            oldest_acceptable_date = today_for_check - timedelta(days=config.RECENCY_THRESHOLD_DAYS - 1)
            if publication_date_dt >= oldest_acceptable_date and publication_date_dt <= today_for_check:
                is_recent_status = f"Recent {date_source_log}"
            elif publication_date_dt > today_for_check:
                is_recent_status = f"Date in future {date_source_log}"
            else:
                is_recent_status = f"Not recent {date_source_log}"
        except ValueError:
            is_recent_status = f"Date unparsable {date_source_log}"
            print(f"Warning: Could not parse final date '{final_date_str}' for {article_url}.")
        
    final_results = {
        "url": article_url,
        "publication_date_str": final_date_str,
        "is_recent": is_recent_status,
        "is_relevant": final_relevance if 'final_relevance' in locals() else "Relevance unclear (init error)",
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
        extracted_date = _extract_date_from_url(test_url)
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