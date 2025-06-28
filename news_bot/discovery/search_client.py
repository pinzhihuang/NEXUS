# news_bot/discovery/search_client.py

import os
import json # For potential direct JSON parsing if needed, though client library handles most
from datetime import date, timedelta
from googleapiclient.discovery import build # For Google Custom Search API
from ..core import config
import requests # For fetching category pages
from bs4 import BeautifulSoup # For parsing category pages
from urllib.parse import urljoin # For resolving relative URLs
import re # For regular expressions

# ...existing code...

def scan_category_pages_for_links() -> list[dict[str, str]]:
    """
    Scans configured category pages for direct links to articles.
    Returns a list of dictionaries, each containing 'title', 'url', 'snippet', and 'preview_date'.
    """
    found_articles = []
    processed_urls = set()

    if not config.CATEGORY_PAGES_TO_SCAN:
        print("Info: No category pages configured to scan.")
        return []

    print("\n--- Scanning Category Pages for Article Links ---")
    for page_url in config.CATEGORY_PAGES_TO_SCAN:
        print(f"Scanning category page: {page_url}")
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(page_url, headers=headers, timeout=config.URL_FETCH_TIMEOUT)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            candidate_links = []
            # --- Emory News: find all article cards in the list ---
            for li in soup.select('li.tag-list-item'):
                link_tag = li.select_one('a[href]')
                title_tag = li.select_one('.tag-list-item-heading')
                date_tag = li.select_one('.tag-list-item-meta')
                if link_tag and title_tag:
                    candidate_links.append({
                        "link_tag": link_tag,
                        "title": title_tag.get_text(strip=True),
                        "date": date_tag.get_text(strip=True) if date_tag else None
                    })

            if not candidate_links:
                print(f"  Info: No candidate article links found via Emory News selector on {page_url}.")

            for item in candidate_links:
                link_tag = item["link_tag"]
                raw_url = link_tag['href']
                title = item["title"]
                preview_date = item["date"]
                absolute_url = urljoin(page_url, raw_url)

                if absolute_url in processed_urls:
                    continue

                # Validate URL structure and domain
                if not absolute_url.startswith("http") or not any(domain in absolute_url for domain in config.TARGET_NEWS_SOURCES_DOMAINS):
                    continue

                # Filter out common non-article paths
                if any(skip_path in absolute_url for skip_path in ["/category/", "/tag/", "/author/"]):
                    print(f"  Skipping likely non-article link: {absolute_url}")
                    continue

                # Heuristic: check for sufficient path depth for articles
                if len(absolute_url.split('/')) > 5:
                    print(f"  Found potential article via category scan: '{title}' -> {absolute_url}")
                    found_articles.append({
                        "title": title,
                        "url": absolute_url,
                        "snippet": title,
                        "preview_date": preview_date
                    })
                    processed_urls.add(absolute_url)
                    if len(found_articles) >= config.MAX_SEARCH_RESULTS_TO_PROCESS * 2:
                        break

            if len(found_articles) >= config.MAX_SEARCH_RESULTS_TO_PROCESS * 2:
                break

        except requests.exceptions.RequestException as e_req:
            print(f"Error fetching category page {page_url}: {e_req}")
        except Exception as e_general:
            print(f"Error processing category page {page_url}: {e_general}")

    print(f"Found {len(found_articles)} unique potential articles from category page scans.")
    return found_articles

# ...existing code...

def find_articles_with_google_pse() -> list[dict[str, str]]:
    """
    Queries the Google Programmable Search Engine (PSE) to find news articles.
    """
    if not config.GOOGLE_API_KEY or not config.CUSTOM_SEARCH_ENGINE_ID:
        print("Info: Google PSE not configured (API Key or CX ID missing). Skipping PSE search.")
        return []

    query = " OR ".join([f'"{keyword.strip()}"' for keyword in config.RELEVANCE_KEYWORDS if keyword.strip()])
    found_articles_from_pse = []
    try:
        service = build("customsearch", "v1", developerKey=config.GOOGLE_API_KEY)
        print(f"\n--- Querying Google PSE (Engine ID: {config.CUSTOM_SEARCH_ENGINE_ID}) ---")
        print(f"PSE Query: {query}")
        today_dt = date.today()
        start_date_dt = today_dt - timedelta(days=config.RECENCY_THRESHOLD_DAYS -1)
        start_date_str = start_date_dt.strftime("%Y%m%d")
        end_date_str = today_dt.strftime("%Y%m%d")
        sort_by_date_range = f"date:r:{start_date_str}:{end_date_str}"
        print(f"PSE Sorting by date range: {sort_by_date_range}")

        res = service.cse().list(
            q=query,
            cx=config.CUSTOM_SEARCH_ENGINE_ID,
            num=config.MAX_SEARCH_RESULTS_TO_PROCESS,
            sort=sort_by_date_range 
        ).execute()

        if 'items' in res:
            for item in res['items']:
                title = item.get('title', 'N/A')
                url = item.get('link')
                snippet = item.get('snippet', '')
                if not url or not url.startswith("http"):
                    print(f"Skipping PSE item with invalid/missing URL: {title if title != 'N/A' else snippet[:50]}")
                    continue
                # Domain check (PSE should already be restricted, but good for sanity)
                if not any(domain in url for domain in config.TARGET_NEWS_SOURCES_DOMAINS):
                    print(f"Skipping PSE item from non-target domain: {url}")
                    continue
                found_articles_from_pse.append({"title": title, "url": url, "snippet": snippet})
            print(f"Retrieved {len(found_articles_from_pse)} articles from Google PSE.")
        else:
            print("No items found in Google PSE response for this query.")
    except Exception as e:
        print(f"An error occurred while querying Google PSE: {e}")
    return found_articles_from_pse

def find_relevant_articles() -> list[dict[str, str]]:
    """
    Main discovery function. Combines results from category scans and Google PSE.
    """
    all_discovered_articles = []
    processed_urls = set()

    articles_from_categories = scan_category_pages_for_links()
    for article in articles_from_categories:
        if article["url"] not in processed_urls:
            article["source_method"] = "category_scan"
            all_discovered_articles.append(article)
            processed_urls.add(article["url"])
    
    articles_from_pse = find_articles_with_google_pse()
    for article in articles_from_pse:
        if article["url"] not in processed_urls:
            article["source_method"] = "google_pse"
            all_discovered_articles.append(article)
            processed_urls.add(article["url"])

    print(f"Total unique articles discovered from all sources: {len(all_discovered_articles)}")
    return all_discovered_articles[:config.MAX_SEARCH_RESULTS_TO_PROCESS]

if __name__ == '__main__':
    print("Testing Discovery Module (Category Scan + Google PSE)...")
    import sys
    # Ensure the project root is in sys.path for relative imports when run directly
    PROJECT_ROOT_FOR_TEST = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if PROJECT_ROOT_FOR_TEST not in sys.path:
         sys.path.insert(0, PROJECT_ROOT_FOR_TEST)
    
    from news_bot.core import config 
    config.validate_config() 

    articles = find_relevant_articles()
    if articles:
        print("\nCombined Discovered Articles:")
        for i, article in enumerate(articles):
            print(f"{i+1}. Title: {article.get('title', 'N/A')} (From: {article.get('source_method', 'Unknown')})\n   URL: {article['url']}")
            if 'snippet' in article and article['snippet'] != article.get('title'): # Avoid printing title as snippet if they are same
                 print(f"   Snippet: {article['snippet'][:100]}...")
    else:
        print("No articles found from any source or an error occurred.") 