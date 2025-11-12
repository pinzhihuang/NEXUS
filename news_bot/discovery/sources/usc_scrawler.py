from datetime import date, timedelta, datetime
from googleapiclient.discovery import build # For Google Custom Search API
from ...core import config, school_config
from ...discovery.date_extractor import extract_date_from_url
from ...utils import prompt_logger, openrouter_client
import requests # For fetching category pages
from bs4 import BeautifulSoup # For parsing category pages
from urllib.parse import urljoin # For resolving relative URLs
import re # For regular expressions
import json


def gemini_verify_article(title: str, description: str) -> str:
    """ 
    Due to the high volumn of articles from USC source, we need to verify the article with OpenRouter by title and description before proceeding
    Returns "Relevant" or "Irrelevant"
    """
    if not config.OPENROUTER_API_KEY:
        return "Irrelevant"
    
    prompt = f"""
    You are a news analyst. Please analyze the following news article by title and description. 
    Is this article generally relevant to students at USC, covering campus news, academic updates, student life, or significant events affecting the USC community? return either "Irrelevant" or "Relevant"
    [some examples of irrelevant articles] If the article is about actor, actress, music star, music, sports star, sports events, sports matches, American/Latin culture study, American Science break through, return "Irrelevant".
    News Title: {title}
    News Description: {description}
    Return either "Relevant" or "Irrelevant".
    """
    
    # Log the prompt
    prompt_logger.log_prompt(
        "gemini_verify_article",
        prompt,
        context={"title": title, "description": description[:200] if len(description) > 200 else description}
    )
    
    try:
        text = openrouter_client.generate_content(
            prompt=prompt,
            model=config.GEMINI_FLASH_MODEL,
            temperature=0.3
        )
        if text:
            return text.strip()
        return "Irrelevant"
    except Exception as e:
        print(f"Error in gemini_verify_article: {e}")
        return "Irrelevant"


def usc_scan_archive_pages_for_date_range() -> list[dict]:
    """
    USC Annenberg uses Arc XP with a "load more" button that fetches JSON via
    the story-feed-query endpoint. We paginate with offset/size until either
    there are no more results or we have enough in-range items.
    """
    school = school_config.SCHOOL_PROFILES['usc']
    start_date, end_date = config.get_news_date_range()
    print(f"\n--- Scanning Archive Pages for {start_date} to {end_date} ---")

    # Use the JSON endpoint listed in school_config.category_pages
    base_api = school['category_pages'][0]

    found_articles: list[dict] = []
    processed_urls: set[str] = set()

    flag = True
    offset = 0
    size = 40
    max_pages = 30  # hard safety cap
    page_count = 0


    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    while flag:
        if page_count >= max_pages:
            print(f"  Reached safety page limit ({max_pages}); stopping.")
            break
        print(f"  USC API request at offset={offset}, size={size} (page {page_count+1})")
        try:
            query_obj = {"feature": "results-list", "offset": offset, "size": size}
            # Minimal filter to reduce payload size
            filter_str = (
                "content_elements{display_date,headlines{basic},description{basic},type,"
                "websites{uscannenberg{website_url}}},count,next"
            )
            params = {
                "query": json.dumps(query_obj, separators=(',', ':')),
                "filter": filter_str,
                "_website": "uscannenberg",
                "d": "101",
            }
            resp = requests.get(base_api, params=params, headers=headers, timeout=config.URL_FETCH_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()

            elements = data.get("content_elements") or []
            if not elements:
                print("  No content_elements; stopping.")
                break

            for el in elements:
                try:
                    if el.get("type") != "story":
                        continue
                    path = (((el.get("websites") or {}).get("uscannenberg") or {}).get("website_url"))
                    if not path:
                        continue
                    abs_url = urljoin("https://www.uscannenbergmedia.com", path)
                    if abs_url in processed_urls:
                        continue

                    title = ((el.get("headlines") or {}).get("basic")) or "Untitled"
                    snippet = ((el.get("description") or {}).get("basic")) or title

                    # Parse display_date from ISO timestamp
                    disp = el.get("display_date")
                    url_date = None
                    article_date = None
                    if disp:
                        try:
                            # fromisoformat needs offset if present; handle 'Z'
                            dt = datetime.fromisoformat(disp.replace('Z', '+00:00'))
                            url_date = dt.date().strftime("%Y-%m-%d")
                            article_date = dt.date()
                            print(f"    DEBUG: Article '{title[:50]}...' has date: {url_date}")
                        except ValueError as e:
                            print(f"    DEBUG: Failed to parse date '{disp}': {e}")
                            url_date = None
                            article_date = None
                    else:
                        print(f"    DEBUG: Article '{title[:50]}...' has NO display_date field")

                    # Filter by configured date range when we have a date
                    if article_date:
                        if article_date < start_date:
                            print(f"    DEBUG: Article date {article_date} is BEFORE start_date {start_date}, stopping pagination")
                            flag = False
                            continue
                        elif article_date > end_date:
                            print(f"    DEBUG: Article date {article_date} is AFTER end_date {end_date}, skipping")
                            continue
                        else:
                            print(f"    DEBUG: Article date {article_date} is IN RANGE ({start_date} to {end_date})")
                    else:
                        # No date - for historical searches, skip articles without dates
                        if config.NEWS_START_DATE:
                            print(f"    DEBUG: Article has no date, skipping (historical search mode)")
                            continue
                        else:
                            print(f"    DEBUG: Article has no date, including for verification (current news mode)")

                    # semantic filter via Gemini
                    try:
                        gemini_result = gemini_verify_article(title, snippet)
                        if gemini_result == "Irrelevant":
                            print(f"    DEBUG: Article filtered by Gemini as Irrelevant")
                            continue
                        else:
                            print(f"    DEBUG: Article passed Gemini relevance check")
                    except Exception as e:
                        print(f"    DEBUG: Gemini verification failed: {e}")
                        pass

                    print(f"    ✓ Adding article: '{title[:50]}...' ({url_date or 'no date'})")
                    found_articles.append({
                        "title": title,
                        "url": abs_url,
                        "snippet": snippet,
                        "url_date": url_date,
                    })
                    processed_urls.add(abs_url)
                    if len(found_articles) >= config.MAX_SEARCH_RESULTS_TO_PROCESS:
                        break
                except Exception:
                    continue

            if len(found_articles) >= config.MAX_SEARCH_RESULTS_TO_PROCESS:
                break

            # Use server-provided next offset if available; otherwise increment
            next_offset = data.get("next")
            if isinstance(next_offset, int) and next_offset > offset:
                offset = next_offset
            else:
                new_offset = offset + size
                if new_offset == offset:
                    print("  Next offset did not advance; stopping to avoid infinite loop.")
                    break
                offset = new_offset
            page_count += 1

        except requests.exceptions.RequestException as e:
            print(f"  Error accessing USC API at offset {offset}: {e}")
            break
        except ValueError as e:
            print(f"  Error parsing USC API response at offset {offset}: {e}")
            break
        except Exception as e:
            print(f"  Unexpected error at offset {offset}: {e}")
            break

    print(f"\nUSC API Summary:")
    print(f"  Total pages scanned: {page_count}")
    print(f"  Articles found in date range ({start_date} to {end_date}): {len(found_articles)}")
    if found_articles:
        print(f"  Sample articles:")
        for i, article in enumerate(found_articles[:5]):
            print(f"    {i+1}. [{article.get('url_date', 'no date')}] {article['title'][:60]}...")
    return found_articles

    
    