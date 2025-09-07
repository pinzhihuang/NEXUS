# news_bot/discovery/search_client.py

import os
import json # For potential direct JSON parsing if needed, though client library handles most
from datetime import date, timedelta, datetime
from googleapiclient.discovery import build # For Google Custom Search API
from ..core import config
from .date_extractor import extract_date_from_url
from .sources.nyu_scrawler import nyu_scan_archive_pages_for_date_range, nyu_scan_category_pages_for_links
from .sources.emory_scrawler import emory_scan_archive_pages_for_date_range
from .sources.ucd_scrawler import ucd_scan_category_pages_for_links
from .sources.ubc_scrawler import ubc_scan_archive_pages_for_date_range
import requests # For fetching category pages
from bs4 import BeautifulSoup # For parsing category pages
from urllib.parse import urljoin # For resolving relative URLs
import re # For regular expressions



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
                        url_date = extract_date_from_url(url)
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

def find_relevant_articles(school: dict[str, str]) -> list[dict[str, str]]:
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
    if school['id'] == 1:
        articles_from_archives = nyu_scan_archive_pages_for_date_range()
    elif school['id'] == 2:
        articles_from_archives = emory_scan_archive_pages_for_date_range()
    elif school['id'] == 3:
        articles_from_archives = ucd_scan_category_pages_for_links()
    elif school['id'] == 4:
        articles_from_archives = ubc_scan_archive_pages_for_date_range()
    else:
        articles_from_archives = []
    for article in articles_from_archives:
        if article["url"] not in processed_urls:
            article["source_method"] = "archive_scan"
            all_discovered_articles.append(article)
            processed_urls.add(article["url"])
    
    # Then scan category pages if we need more articles (NYU only)
    if school['id'] == 1 and len(all_discovered_articles) < config.MAX_SEARCH_RESULTS_TO_PROCESS:
        print(f"Found {len(all_discovered_articles)} articles from archives, scanning category pages for more...")
        articles_from_categories = nyu_scan_category_pages_for_links()
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
                            # Don't print for every article, just count
                            pass
                    except ValueError:
                        # If date parsing fails, include the article for further verification
                        all_discovered_articles.append(article)
                        processed_urls.add(article["url"])
                else:
                    # No date in URL, include for further verification if not doing historical search
                    if not config.NEWS_START_DATE:
                        all_discovered_articles.append(article)
                        processed_urls.add(article["url"])
    
    # Finally, try Google PSE if we still need more articles
    if len(all_discovered_articles) < config.MAX_SEARCH_RESULTS_TO_PROCESS:
        print(f"Found {len(all_discovered_articles)} articles so far, trying Google PSE for more...")
        articles_from_pse = find_articles_with_google_pse()
        for article in articles_from_pse:
            if article["url"] not in processed_urls:
                article["source_method"] = "google_pse"
                all_discovered_articles.append(article)
                processed_urls.add(article["url"])

    print(f"\nTotal unique articles discovered from all sources: {len(all_discovered_articles)}")
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
                    return (2, abs((article_date - start_date).days))  # Priority 2, sorted by distance from range
            except ValueError:
                pass
        return (1, 999)  # Priority 1 for no date
    
    all_discovered_articles.sort(key=sort_key)
    
    # Show what we're returning
    limited_articles = all_discovered_articles[:config.MAX_SEARCH_RESULTS_TO_PROCESS]
    print(f"\nReturning top {len(limited_articles)} articles for processing:")
    for i, article in enumerate(limited_articles[:5]):  # Show first 5
        date_str = article.get('url_date', 'no date')
        print(f"  {i+1}. [{date_str}] {article['title'][:50]}...")
    if len(limited_articles) > 5:
        print(f"  ... and {len(limited_articles) - 5} more")
    
    return limited_articles

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