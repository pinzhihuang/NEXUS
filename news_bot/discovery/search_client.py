# news_bot/discovery/search_client.py

import os
import json # For potential direct JSON parsing if needed, though client library handles most
from datetime import date, timedelta, datetime
from googleapiclient.discovery import build # For Google Custom Search API
from ..core import config
import requests # For fetching category pages
from bs4 import BeautifulSoup # For parsing category pages
from urllib.parse import urljoin # For resolving relative URLs
import re # For regular expressions

def _extract_date_from_url(url_string: str) -> str | None:
    """
    Attempts to extract a date (YYYY-MM-DD) from a URL string.
    Looks for various date patterns commonly used in news URLs.
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
    return None

def scan_archive_pages_for_date_range() -> list[dict[str, str]]:
    """
    Scans archive pages for articles within the configured date range.
    Uses ARCHIVE_URL_PATTERNS from config to construct date-specific URLs.
    """
    found_articles = []
    processed_urls = set()
    
    if not hasattr(config, 'ARCHIVE_URL_PATTERNS') or not config.ARCHIVE_URL_PATTERNS:
        print("Info: No archive URL patterns configured.")
        return []
    
    start_date, end_date = config.get_news_date_range()
    print(f"\n--- Scanning Archive Pages for {start_date} to {end_date} ---")
    
    # Generate list of dates to check
    current_date = start_date
    dates_to_check = []
    while current_date <= end_date:
        dates_to_check.append(current_date)
        current_date += timedelta(days=1)
    
    # Group dates by month for monthly archives
    months_to_check = {}
    for check_date in dates_to_check:
        month_key = (check_date.year, check_date.month)
        if month_key not in months_to_check:
            months_to_check[month_key] = []
        months_to_check[month_key].append(check_date)
    
    for pattern in config.ARCHIVE_URL_PATTERNS:
        for (year, month), dates_in_month in months_to_check.items():
            # Construct archive URL - handle formatting properly
            try:
                # Format month with zero padding
                archive_url = pattern.replace("{year}", str(year)).replace("{month:02d}", f"{month:02d}")
            except Exception:
                # Fallback for simpler format strings
                archive_url = pattern.format(year=year, month=month, day=1)
            
            print(f"Checking archive: {archive_url}")
            
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                response = requests.get(archive_url, headers=headers, timeout=config.URL_FETCH_TIMEOUT)
                
                if response.status_code == 404:
                    print(f"  Archive page not found: {archive_url}")
                    continue
                
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Find all links that look like articles
                article_links = []
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    absolute_url = urljoin(archive_url, href)
                    
                    # Check if it's an article URL
                    if any(domain in absolute_url for domain in config.TARGET_NEWS_SOURCES_DOMAINS):
                        if re.search(r'/\d{4}/\d{2}/\d{2}/', absolute_url) or re.search(r'news/\d{4}/\d{2}/', absolute_url):
                            article_links.append((link, absolute_url))
                
                # Process found links
                articles_found_in_archive = 0
                for link, absolute_url in article_links:
                    if absolute_url in processed_urls:
                        continue
                    
                    title = link.get_text(strip=True)
                    if not title:
                        continue
                    
                    # Extract date from URL
                    url_date = _extract_date_from_url(absolute_url)
                    if url_date:
                        try:
                            article_date = datetime.strptime(url_date, "%Y-%m-%d").date()
                            if article_date >= start_date and article_date <= end_date:
                                print(f"  Found article in archive: {title[:50]}... ({url_date})")
                                found_articles.append({
                                    "title": title,
                                    "url": absolute_url,
                                    "snippet": title,
                                    "url_date": url_date
                                })
                                processed_urls.add(absolute_url)
                                articles_found_in_archive += 1
                        except ValueError:
                            pass
                
                if articles_found_in_archive > 0:
                    print(f"  Found {articles_found_in_archive} relevant articles in this archive")
                
            except requests.exceptions.RequestException as e:
                print(f"  Error accessing archive {archive_url}: {e}")
            except Exception as e:
                print(f"  Error processing archive {archive_url}: {e}")
    
    print(f"Found {len(found_articles)} articles from archive pages")
    return found_articles

def scan_category_pages_for_links() -> list[dict[str, str]]:
    """
    Scans configured category pages for direct links to articles.
    Attempts to scan multiple pages to find articles within the configured date range.
    Returns a list of dictionaries, each containing 'title', 'url', and 'snippet' (title used as snippet).
    """
    found_articles = []
    processed_urls = set()

    if not config.CATEGORY_PAGES_TO_SCAN:
        print("Info: No category pages configured to scan.")
        return []

    # Get the configured date range for filtering
    start_date, end_date = config.get_news_date_range()
    print(f"\n--- Scanning Category Pages for Article Links (targeting {start_date} to {end_date}) ---")
    
    for page_url in config.CATEGORY_PAGES_TO_SCAN:
        # Try to scan multiple pages if the site supports pagination
        max_pages = 20  # Scan up to 20 pages to find older articles
        for page_num in range(1, max_pages + 1):
            # Construct paginated URL (common patterns)
            if page_num == 1:
                current_page_url = page_url
            else:
                # Try common pagination patterns
                if page_url.endswith('/'):
                    current_page_url = f"{page_url}page/{page_num}/"
                else:
                    current_page_url = f"{page_url}/page/{page_num}/"
            
            print(f"Scanning category page {page_num}: {current_page_url}")
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                response = requests.get(current_page_url, headers=headers, timeout=config.URL_FETCH_TIMEOUT)
                
                # If pagination doesn't exist, break the loop
                if page_num > 1 and response.status_code == 404:
                    print(f"  Page {page_num} not found, stopping pagination.")
                    break
                    
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')

                candidate_links = []
                # General approach: find links within heading tags, common in article listings.
                for heading_tag_name in ['h1', 'h2', 'h3', 'h4']:
                    for heading_element in soup.find_all(heading_tag_name):
                        link_tag = heading_element.find('a', href=True)
                        if link_tag:
                            candidate_links.append(link_tag)
                
                # Also look for article links in common article containers
                for article_container in soup.find_all(['article', 'div'], class_=re.compile(r'(post|article|entry|news-item)', re.I)):
                    for link in article_container.find_all('a', href=True):
                        if link not in candidate_links:
                            candidate_links.append(link)
                
                if not candidate_links:
                    print(f"  Info: No candidate article links found on page {page_num}.")
                    continue

                articles_found_on_page = 0
                for link_tag in candidate_links:
                    raw_url = link_tag['href']
                    title = link_tag.get_text(strip=True)
                    absolute_url = urljoin(current_page_url, raw_url)

                    if absolute_url in processed_urls or not title:
                        continue

                    # Validate URL structure and domain
                    if not absolute_url.startswith("http") or not any(domain in absolute_url for domain in config.TARGET_NEWS_SOURCES_DOMAINS):
                        continue

                    # Filter out common non-article paths
                    if any(skip_path in absolute_url for skip_path in ["/category/", "/tag/", "/author/", "/page/"]):
                        continue
                    
                    # Extract date from URL if possible
                    url_date = _extract_date_from_url(absolute_url)
                    
                    # Check if URL contains a date pattern or has sufficient depth
                    if re.search(r'/\d{4}/\d{2}/\d{2}/', absolute_url) or re.search(r'/\d{4}/\d{2}/', absolute_url) or len(absolute_url.split('/')) > 5:
                        # If we can extract a date, check if it's in our range
                        if url_date:
                            try:
                                article_date = datetime.strptime(url_date, "%Y-%m-%d").date()
                                if article_date < start_date:
                                    print(f"  Article date {url_date} is before target range, continuing to scan...")
                                    # Continue scanning but don't break - older articles might be mixed
                                elif article_date > end_date:
                                    print(f"  Article date {url_date} is after target range, skipping...")
                                    continue
                                else:
                                    print(f"  Found article in target range: '{title[:50]}...' ({url_date})")
                            except ValueError:
                                pass  # If date parsing fails, include the article anyway
                        
                        found_articles.append({"title": title, "url": absolute_url, "snippet": title, "url_date": url_date})
                        processed_urls.add(absolute_url)
                        articles_found_on_page += 1
                        
                        if len(found_articles) >= config.MAX_SEARCH_RESULTS_TO_PROCESS * 3:  # Allow more articles for date filtering
                            break
                
                print(f"  Found {articles_found_on_page} potential articles on page {page_num}")
                
                # If we've found enough articles or no articles on this page, stop pagination
                if len(found_articles) >= config.MAX_SEARCH_RESULTS_TO_PROCESS * 3 or articles_found_on_page == 0:
                    break
                    
            except requests.exceptions.RequestException as e_req:
                print(f"Error fetching category page {current_page_url}: {e_req}")
                if page_num == 1:
                    break  # If first page fails, don't try pagination
            except Exception as e_general:
                print(f"Error processing category page {current_page_url}: {e_general}")
    
    print(f"Found {len(found_articles)} unique potential articles from category page scans.")
    
    # Sort articles by date if available (newest first for consistency)
    found_articles.sort(key=lambda x: x.get('url_date') or '9999-99-99', reverse=True)
    
    return found_articles

def find_articles_with_google_pse() -> list[dict[str, str]]:
    """
    Queries the Google Programmable Search Engine (PSE) to find news articles.
    Uses the configured date range from config.get_news_date_range().
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
        
        # Use the configured date range
        start_date, end_date = config.get_news_date_range()
        
        # Try multiple search strategies for better date-specific results
        search_strategies = [
            # Strategy 1: Use dateRestrict parameter (searches within last N days)
            {"use_date_restrict": True},
            # Strategy 2: Add date to query
            {"add_date_to_query": True},
            # Strategy 3: Use sort parameter
            {"use_sort": True}
        ]
        
        for strategy in search_strategies:
            if len(found_articles_from_pse) >= config.MAX_SEARCH_RESULTS_TO_PROCESS:
                break
                
            search_params = {
                "q": query,
                "cx": config.CUSTOM_SEARCH_ENGINE_ID,
                "num": min(10, config.MAX_SEARCH_RESULTS_TO_PROCESS - len(found_articles_from_pse))
            }
            
            if strategy.get("use_date_restrict"):
                # Calculate days difference from today
                days_ago = (date.today() - start_date).days
                if days_ago > 0:
                    search_params["dateRestrict"] = f"d{min(days_ago + 7, 365)}"  # Cap at 365 days
                    print(f"PSE Strategy: Using dateRestrict for last {min(days_ago + 7, 365)} days")
            elif strategy.get("add_date_to_query"):
                # Add date range to query
                date_query = f"{query} after:{start_date.strftime('%Y-%m-%d')} before:{end_date.strftime('%Y-%m-%d')}"
                search_params["q"] = date_query
                print(f"PSE Strategy: Adding date range to query")
            elif strategy.get("use_sort"):
                # Use sort parameter
                start_date_str = start_date.strftime("%Y%m%d")
                end_date_str = end_date.strftime("%Y%m%d")
                search_params["sort"] = f"date:r:{start_date_str}:{end_date_str}"
                print(f"PSE Strategy: Using sort parameter for {start_date} to {end_date}")
            
            try:
                res = service.cse().list(**search_params).execute()
                
                if 'items' in res:
                    for item in res['items']:
                        title = item.get('title', 'N/A')
                        url = item.get('link')
                        snippet = item.get('snippet', '')
                        
                        # Skip if already found
                        if any(a['url'] == url for a in found_articles_from_pse):
                            continue
                            
                        if not url or not url.startswith("http"):
                            continue
                        
                        # Domain check
                        if not any(domain in url for domain in config.TARGET_NEWS_SOURCES_DOMAINS):
                            continue
                        
                        # Try to extract date from URL for filtering
                        url_date = _extract_date_from_url(url)
                        if url_date:
                            try:
                                article_date = datetime.strptime(url_date, "%Y-%m-%d").date()
                                if article_date < start_date or article_date > end_date:
                                    print(f"  PSE result outside date range: {url_date} - {title[:50]}...")
                                    continue
                            except ValueError:
                                pass
                        
                        found_articles_from_pse.append({
                            "title": title, 
                            "url": url, 
                            "snippet": snippet,
                            "url_date": url_date
                        })
                    
                    print(f"  Strategy yielded {len(res.get('items', []))} results, {len(found_articles_from_pse)} within date range")
                else:
                    print(f"  Strategy yielded no results")
                    
            except Exception as e:
                print(f"  Strategy failed: {e}")
                continue
        
        print(f"Retrieved {len(found_articles_from_pse)} articles from Google PSE after all strategies.")
        
    except Exception as e:
        print(f"An error occurred while querying Google PSE: {e}")
    
    return found_articles_from_pse

def find_relevant_articles() -> list[dict[str, str]]:
    """
    Main discovery function. Combines results from archive pages, category scans, and Google PSE.
    Filters articles to match the configured date range.
    """
    all_discovered_articles = []
    processed_urls = set()
    
    # Get configured date range for filtering
    start_date, end_date = config.get_news_date_range()
    print(f"\nSearching for articles from {start_date} to {end_date}")

    # First, try archive pages for specific dates (most targeted approach)
    articles_from_archives = scan_archive_pages_for_date_range()
    for article in articles_from_archives:
        if article["url"] not in processed_urls:
            article["source_method"] = "archive_scan"
            all_discovered_articles.append(article)
            processed_urls.add(article["url"])
    
    # Then scan category pages if we need more articles
    if len(all_discovered_articles) < config.MAX_SEARCH_RESULTS_TO_PROCESS:
        articles_from_categories = scan_category_pages_for_links()
        for article in articles_from_categories:
            if article["url"] not in processed_urls:
                article["source_method"] = "category_scan"
                
                # Additional date filtering if date was extracted
                if article.get("url_date"):
                    try:
                        article_date = datetime.strptime(article["url_date"], "%Y-%m-%d").date()
                        if article_date >= start_date and article_date <= end_date:
                            all_discovered_articles.append(article)
                            processed_urls.add(article["url"])
                        else:
                            print(f"  Filtering out article from {article['url_date']}: {article['title'][:50]}...")
                    except ValueError:
                        # If date parsing fails, include the article for further verification
                        all_discovered_articles.append(article)
                        processed_urls.add(article["url"])
                else:
                    # No date in URL, include for further verification
                    all_discovered_articles.append(article)
                    processed_urls.add(article["url"])
    
    # Finally, try Google PSE if we still need more articles
    if len(all_discovered_articles) < config.MAX_SEARCH_RESULTS_TO_PROCESS:
        articles_from_pse = find_articles_with_google_pse()
        for article in articles_from_pse:
            if article["url"] not in processed_urls:
                article["source_method"] = "google_pse"
                all_discovered_articles.append(article)
                processed_urls.add(article["url"])

    print(f"Total unique articles discovered from all sources: {len(all_discovered_articles)}")
    print(f"  - From archives: {len([a for a in all_discovered_articles if a.get('source_method') == 'archive_scan'])}")
    print(f"  - From categories: {len([a for a in all_discovered_articles if a.get('source_method') == 'category_scan'])}")
    print(f"  - From Google PSE: {len([a for a in all_discovered_articles if a.get('source_method') == 'google_pse'])}")
    
    # Prioritize articles with dates in the target range
    def sort_key(article):
        if article.get("url_date"):
            try:
                article_date = datetime.strptime(article["url_date"], "%Y-%m-%d").date()
                if start_date <= article_date <= end_date:
                    return (0, article_date)  # Priority 0 for in-range dates
                else:
                    return (2, article_date)  # Priority 2 for out-of-range dates
            except ValueError:
                pass
        return (1, date.today())  # Priority 1 for no date
    
    all_discovered_articles.sort(key=sort_key)
    
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