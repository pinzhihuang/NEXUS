import os
import json # For potential direct JSON parsing if needed, though client library handles most
from datetime import date, timedelta, datetime
from googleapiclient.discovery import build # For Google Custom Search API
from ...core import config, school_config
from ...discovery.date_extractor import extract_date_from_url
import requests # For fetching category pages
from bs4 import BeautifulSoup # For parsing category pages
from urllib.parse import urljoin # For resolving relative URLs
import re # For regular expressions



def nyu_scan_archive_pages_for_date_range() -> list[dict[str, str]]:
    """
    Scans archive pages for articles within the configured date range.
    Uses ARCHIVE_URL_PATTERNS from config to construct date-specific URLs.
    """
    found_articles = []
    processed_urls = set()
    school = school_config.SCHOOL_PROFILES['nyu']
    
    if not hasattr(config, 'ARCHIVE_URL_PATTERNS') or not school.get('archive_patterns'):
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
    
    for pattern in school.get('archive_patterns'):
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
                    
                    # Check if it's an article URL with proper domain
                    if not any(domain in absolute_url for domain in school.get('domains')):
                        continue
                    
                    # Filter out non-article URLs
                    skip_patterns = [
                        "/staff_name/", "/staff/", "/writer/", "/contributor/",
                        "/category/", "/tag/", "/author/", "/page/",
                        "/about/", "/contact/", "/privacy/", "/terms/",
                        "#", "javascript:", "mailto:"
                    ]
                    if any(skip_path in absolute_url.lower() for skip_path in skip_patterns):
                        continue
                    
                    # Check for news article patterns
                    if "nyunews.com" in absolute_url:
                        if re.search(r'/news/\d{4}/\d{2}/\d{2}/', absolute_url) or \
                           re.search(r'/\d{4}/\d{2}/\d{2}/\w+/', absolute_url):
                            article_links.append((link, absolute_url))
                    elif re.search(r'/\d{4}/\d{2}/\d{2}/', absolute_url) or re.search(r'news/\d{4}/\d{2}/', absolute_url):
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
                    url_date = extract_date_from_url(absolute_url)
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

def nyu_scan_category_pages_for_links() -> list[dict[str, str]]:
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
        max_pages = config.MAX_CATEGORY_PAGES_TO_SCAN  # Use config value
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
                
                # Method 1: Find links within heading tags (common in article listings)
                for heading_tag_name in ['h1', 'h2', 'h3', 'h4', 'h5']:
                    for heading_element in soup.find_all(heading_tag_name):
                        link_tag = heading_element.find('a', href=True)
                        if link_tag and link_tag not in candidate_links:
                            # Quick pre-filter for news URLs
                            href = link_tag.get('href', '')
                            if '/news/' in href or '/new/' in href or re.search(r'/\d{4}/\d{2}/', href):
                                candidate_links.append(link_tag)
                                print(f"  Found link in heading tag: {link_tag.get_text(strip=True)}")
                
                # Method 2: Look for article links in common article containers
                article_selectors = [
                    'article', 
                    'div.post', 'div.article', 'div.entry', 'div.news-item',
                    'div.story', 'div.content-item', 'div.list-item',
                    'li.post', 'li.article', 'li.news-item'
                ]
                
                for selector in article_selectors:
                    if '.' in selector:
                        tag_name, class_name = selector.split('.', 1)
                        elements = soup.find_all(tag_name, class_=re.compile(class_name, re.I))
                    else:
                        elements = soup.find_all(selector)
                    
                    for container in elements:
                        # Find the main link in the container (usually the title link)
                        title_link = container.find('a', href=True)
                        if title_link and title_link not in candidate_links:
                            href = title_link.get('href', '')
                            if '/news/' in href or '/new/' in href or re.search(r'/\d{4}/\d{2}/', href):
                                candidate_links.append(title_link)
                
                # Method 3: Find links with date patterns in URL
                for link in soup.find_all('a', href=True):
                    href = link.get('href', '')
                    if link not in candidate_links:
                        # Check if URL has date pattern
                        if re.search(r'/(news|new)/\d{4}/\d{2}/\d{2}/', href) or \
                           re.search(r'/\d{4}/\d{2}/\d{2}/', href):
                            candidate_links.append(link)
                
                if not candidate_links:
                    print(f"  Info: No candidate article links found on page {page_num}.")
                    continue

                print(f"  Found {len(candidate_links)} candidate links on page {page_num}")

                articles_found_on_page = 0
                filtered_count = {"no_title": 0, "duplicate": 0, "wrong_domain": 0, "bad_pattern": 0, "out_of_range": 0}
                
                for link_tag in candidate_links:
                    raw_url = link_tag['href']
                    title = link_tag.get_text(strip=True)
                    absolute_url = urljoin(current_page_url, raw_url)

                    if not title:
                        filtered_count["no_title"] += 1
                        continue
                        
                    if absolute_url in processed_urls:
                        filtered_count["duplicate"] += 1
                        continue

                    # Validate URL structure and domain
                    if not absolute_url.startswith("http") or not any(domain in absolute_url for domain in config.TARGET_NEWS_SOURCES_DOMAINS):
                        filtered_count["wrong_domain"] += 1
                        continue

                    # Filter out common non-article paths (expanded list)
                    skip_patterns = [
                        "/category/", "/tag/", "/author/", "/page/",
                        "/staff_name/", "/staff/", "/writer/", "/contributor/",
                        "/about/", "/contact/", "/privacy/", "/terms/",
                        "/subscribe/", "/newsletter/", "/membership/",
                        "/search/", "/archive/", "/topic/",
                        "#", "javascript:", "mailto:"
                    ]
                    if any(skip_path in absolute_url.lower() for skip_path in skip_patterns):
                        filtered_count["bad_pattern"] += 1
                        continue
                    
                    # For NYU news sites, we expect specific URL patterns for articles
                    is_valid_article = False
                    
                    # Check for NYU news patterns
                    if "nyunews.com" in absolute_url:
                        # Valid patterns: /news/YYYY/MM/DD/title or /YYYY/MM/DD/section/title
                        if re.search(r'/(news|new)/\d{4}/\d{2}/\d{2}/', absolute_url) or \
                           re.search(r'/\d{4}/\d{2}/\d{2}/\w+/', absolute_url):
                            is_valid_article = True
                    elif "nyu.edu" in absolute_url:
                        # NYU.edu news patterns
                        if "/news/" in absolute_url or "/news-publications/" in absolute_url:
                            is_valid_article = True
                    else:
                        # For other domains, check for date patterns
                        if re.search(r'/\d{4}/\d{2}/\d{2}/', absolute_url) or \
                           re.search(r'/\d{4}/\d{2}/', absolute_url):
                            is_valid_article = True
                    
                    if not is_valid_article:
                        filtered_count["bad_pattern"] += 1
                        continue
                    
                    # Extract date from URL if possible
                    url_date = extract_date_from_url(absolute_url)
                    
                    # For valid articles, check if they're in our date range
                    if url_date:
                        try:
                            article_date = datetime.strptime(url_date, "%Y-%m-%d").date()
                            if article_date < start_date:
                                # Continue scanning but don't break - older articles might be mixed
                                pass
                            elif article_date > end_date:
                                filtered_count["out_of_range"] += 1
                                continue
                            else:
                                print(f"    ✓ Found article in target range: '{title[:50]}...' ({url_date})")
                                found_articles.append({"title": title, "url": absolute_url, "snippet": title, "url_date": url_date})
                                processed_urls.add(absolute_url)
                                articles_found_on_page += 1
                        except ValueError:
                            pass  # If date parsing fails, include the article anyway
                    else:
                        # No date in URL - skip for historical searches unless it's a special case
                        if config.NEWS_START_DATE:  # If we're doing a historical search
                            filtered_count["bad_pattern"] += 1
                            continue
                        else:
                            # For current news, include articles without dates for verification
                            found_articles.append({"title": title, "url": absolute_url, "snippet": title, "url_date": url_date})
                            processed_urls.add(absolute_url)
                            articles_found_on_page += 1
                    
                    if len(found_articles) >= config.MAX_SEARCH_RESULTS_TO_PROCESS * 3:  # Allow more articles for date filtering
                        break
                
                print(f"  Page {page_num} results: {articles_found_on_page} kept, filtered: {sum(filtered_count.values())} total")
                if sum(filtered_count.values()) > 0:
                    print(f"    Filtered: no_title={filtered_count['no_title']}, duplicate={filtered_count['duplicate']}, " +
                          f"wrong_domain={filtered_count['wrong_domain']}, bad_pattern={filtered_count['bad_pattern']}, " +
                          f"out_of_range={filtered_count['out_of_range']}")
                
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
    found_articles.sort(key=lambda x: x.get('url_date', '9999-99-99'), reverse=True)
    
    return found_articles