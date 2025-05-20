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

def scan_category_pages_for_links() -> list[dict[str, str]]:
    """
    Scans configured category pages for direct links to articles.

    Returns:
        A list of dictionaries, where each dictionary contains 'title' and 'url' of an article.
    """
    found_articles_from_scan = []
    processed_urls = set()

    if not config.CATEGORY_PAGES_TO_SCAN:
        print("No category pages configured to scan.")
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

            # Attempt to find article links. This will likely need site-specific selectors.
            # For nyunews.com, based on snippet, links seem to be in <h2><a> or similar common article listing patterns.
            # Common patterns for article links within listings:
            # - Links within <h1>, <h2>, <h3> tags that are direct children of main content areas
            # - Links with class names like "entry-title", "post-title", "article-link"
            
            # Let's try a few common selectors for WSN structure based on observed patterns:
            # This selector looks for <a> tags inside <h2> that have a class containing 'title'
            # or <a> tags that are children of elements with class 'article-content' or similar.
            # More generally, links within common article listing elements.
            
            # Example from WSN HTML: <h2><a href="...">Title</a></h2>
            # Also, entries under a div with class like "td-module-thumb" or similar can have titles in <h3> or <h4>
            
            # Broad search for links within heading tags often found in listings:
            candidate_links = []
            for heading_tag in ['h1', 'h2', 'h3', 'h4']:
                for heading in soup.find_all(heading_tag):
                    link_tag = heading.find('a', href=True)
                    if link_tag:
                        candidate_links.append(link_tag)
            
            # Look for common WP theme patterns or specific WSN structures if identifiable
            # For instance, articles might be within <article> tags or divs with class "post", "entry", "td-module-meta-info"
            # This is a generic attempt; more specific selectors might be needed after inspecting the page more thoroughly.
            # If the above is too broad, we can try more specific selectors like:
            # potential_article_elements = soup.select('.td_module_wrap .entry-title a, .td-animation-stack .td-post-vid-sm a') # Example specific classes
            # for link_tag in potential_article_elements:
            #    candidate_links.append(link_tag)

            if not candidate_links:
                 print(f"  No candidate links found with general heading search on {page_url}.")

            for link_tag in candidate_links:
                raw_url = link_tag['href']
                title = link_tag.get_text(strip=True)
                
                # Resolve relative URLs to absolute URLs
                absolute_url = urljoin(page_url, raw_url)

                if absolute_url in processed_urls:
                    continue

                # Basic validation: must be http/https and within a target domain (primarily the domain of the category page itself)
                if absolute_url.startswith("http") and any(domain in absolute_url for domain in config.TARGET_NEWS_SOURCES_DOMAINS):
                    # Further check: avoid linking back to a category page or a non-article page like /author/ /tag/
                    if "/category/" in absolute_url or "/tag/" in absolute_url or "/author/" in absolute_url:
                        print(f"  Skipping likely non-article link from category scan: {absolute_url}")
                        continue
                    
                    # Corrected regex: removed the erroneous |''
                    if re.search(r'/\d{4}/\d{2}/\d{2}/', absolute_url) or len(absolute_url.split('/')) > 5:
                        print(f"  Found potential article via category scan: '{title}' -> {absolute_url}")
                        found_articles_from_scan.append({"title": title, "url": absolute_url, "snippet": title}) # Use title as snippet
                        processed_urls.add(absolute_url)
                        if len(found_articles_from_scan) >= config.MAX_SEARCH_RESULTS_TO_PROCESS * 2:
                            break # Break from inner loop (candidate_links)
                    else:
                        print(f"  Skipping link from category scan (heuristic filter): {absolute_url}")
                # else:
                #     print(f"  Skipping link (not http or not in target domains): {absolute_url}")
            if len(found_articles_from_scan) >= config.MAX_SEARCH_RESULTS_TO_PROCESS * 2:
                break # Break from outer loop (CATEGORY_PAGES_TO_SCAN) if limit reached across pages

        except requests.exceptions.RequestException as e_req:
            print(f"Error fetching category page {page_url}: {e_req}")
        except Exception as e_general:
            print(f"Error processing category page {page_url}: {e_general}")
    
    print(f"Found {len(found_articles_from_scan)} unique potential articles from category page scans.")
    return found_articles_from_scan

def find_articles_with_google_pse() -> list[dict[str, str]]:
    """
    Queries the Google Programmable Search Engine (PSE) to find news articles.
    (This is the original function, renamed)
    """
    if not config.GOOGLE_API_KEY or not config.CUSTOM_SEARCH_ENGINE_ID:
        print("Error: GOOGLE_API_KEY or CUSTOM_SEARCH_ENGINE_ID not configured for PSE.")
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
                if not url:
                    continue
                if not any(domain in url for domain in config.TARGET_NEWS_SOURCES_DOMAINS):
                    continue
                found_articles_from_pse.append({"title": title, "url": url, "snippet": snippet})
            print(f"Retrieved {len(found_articles_from_pse)} articles from Google PSE.")
        else:
            print("No items found in Google PSE response.")
    except Exception as e:
        print(f"An error occurred while querying Google PSE: {e}")
    return found_articles_from_pse

def find_relevant_articles() -> list[dict[str, str]]:
    """
    Main discovery function. Combines results from category scans and Google PSE.
    """
    all_discovered_articles = []
    processed_urls = set()

    # 1. Scan category pages
    articles_from_categories = scan_category_pages_for_links()
    for article in articles_from_categories:
        if article["url"] not in processed_urls:
            all_discovered_articles.append(article)
            processed_urls.add(article["url"])
    
    # 2. Use Google PSE for broader search (if configured and needed)
    if config.GOOGLE_API_KEY and config.CUSTOM_SEARCH_ENGINE_ID: # Check if PSE is configured
        articles_from_pse = find_articles_with_google_pse()
        for article in articles_from_pse:
            if article["url"] not in processed_urls:
                # We can add a basic keyword check for title/snippet from PSE results here if needed
                # to ensure they are somewhat relevant before adding, as PSE results can be broad.
                # For now, we rely on later Gemini check for relevance.
                all_discovered_articles.append(article)
                processed_urls.add(article["url"])
    else:
        print("Google PSE not configured, skipping PSE search.")

    print(f"Total unique articles discovered from all sources: {len(all_discovered_articles)}")
    # Optionally, sort all_discovered_articles by some criteria (e.g., if date was part of discovery)
    # or limit to MAX_SEARCH_RESULTS_TO_PROCESS overall.
    return all_discovered_articles[:config.MAX_SEARCH_RESULTS_TO_PROCESS] # Limit total results

if __name__ == '__main__':
    print("Testing Discovery Module (Category Scan + Google PSE)...")
    import sys
    if '..'.join(os.path.abspath(__file__).split(os.sep)[:-2]) not in sys.path:
         sys.path.insert(0, '..'.join(os.path.abspath(__file__).split(os.sep)[:-2]))
    
    from news_bot.core import config 
    config.validate_config() 

    articles = find_relevant_articles()
    if articles:
        print("\nCombined Discovered Articles:")
        for i, article in enumerate(articles):
            print(f"{i+1}. Title: {article.get('title', 'N/A')} ({article.get('source', 'Unknown Source')})\n   URL: {article['url']}")
            if 'snippet' in article:
                 print(f"   Snippet: {article['snippet'][:100]}...")
    else:
        print("No articles found from any source or an error occurred.") 