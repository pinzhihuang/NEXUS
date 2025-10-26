import re
from datetime import datetime, date, timedelta
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from ...discovery.date_extractor import extract_date_from_url, extract_ymd_from_text
from ...core import config, school_config

school = school_config.SCHOOL_PROFILES['emory']

def _month_iter(start_date: date, end_date: date):
    y, m = start_date.year, start_date.month
    while True:
        yield y, m
        if y == end_date.year and m == end_date.month:
            break
        m += 1
        if m == 13:
            m = 1
            y += 1


def emory_scan_wheel_pages_for_date_range() -> list[dict]:
    start_date, end_date = config.get_news_date_range()
    print(f"\n--- Scanning Archive Pages for {start_date} to {end_date} ---")
    
    found_articles: list[dict] = []
    processed_urls: set[str] = set()

    if not school.get('category_pages'):
        return []

    # Emory uses a monthly index page
    page_url = school['category_pages'][1]  # https://www.emorywheel.com/section/news?page=1&per_page=20
    # Try to scan multiple pages if the site supports pagination
    max_pages = config.MAX_CATEGORY_PAGES_TO_SCAN  # Use config value    
    break_signal = False
    
    for page_num in range(1, max_pages):
        if break_signal:
            break
        current_page_url = f"{page_url}?page={page_num}&per_page=20"
        print(f"Checking Emory wheel page: {current_page_url}")
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            resp = requests.get(current_page_url, headers=headers, timeout=config.URL_FETCH_TIMEOUT)
            if resp.status_code == 404:
                print(f"  Page not found: {current_page_url}")
                continue
            resp.raise_for_status()
            soup = BeautifulSoup(resp.content, 'html.parser')
            
            
            for article in soup.find_all('article'):
                a = article.find_all('a', href=True)[1]
                href = a['href']
                abs_url = urljoin(current_page_url, href)
                if 'emorywheel.com/article/' not in abs_url:
                    continue
                if abs_url in processed_urls:
                    continue
                
                title = a['title'] or 'Untitled'
                url_date = article.find_all('span', class_='dateline')[1].get_text(strip=True)
                url_date = extract_ymd_from_text(url_date)
                
                # Compare dates only after converting to a date object
                if url_date:
                    try:
                        article_date = datetime.strptime(url_date, '%Y-%m-%d').date()
                        if article_date < start_date:
                            break_signal = True                       
                        if article_date < start_date or article_date > end_date:
                            print(start_date, url_date, end_date)
                            continue
                    except ValueError:
                        # If parsing fails, keep the article without filtering by date
                        pass       
                
                found_articles.append({
                    'title': title,
                    'url': abs_url,
                    'snippet': title,
                    'url_date': url_date
                })
                processed_urls.add(abs_url)
                
        except requests.exceptions.RequestException as e:
            print(f"  Error accessing Emory wheel page {current_page_url}: {e}")
        except Exception as e:
            print(f"  Error processing Emory wheel page {current_page_url}: {e}")

    print(f"Emory wheel pages yielded {len(found_articles)} articles in range")
    return found_articles



def emory_scan_edu_pages_for_date_range() -> list[dict]:
    start_date, end_date = config.get_news_date_range()
    print(f"\n--- Scanning Archive Pages for {start_date} to {end_date} ---")
    
    found_articles: list[dict] = []
    processed_urls: set[str] = set()

    if not school.get('archive_patterns'):
        return []

    # Emory uses a monthly index page
    monthly_pattern = school['archive_patterns'][0]  # https://news.emory.edu/stories/{year}/{month:02d}/index.html

    for y, m in _month_iter(start_date, end_date):
        # get the archive url for the month
        archive_url = monthly_pattern.format(year=y, month=m)
        print(f"Checking Emory monthly archive: {archive_url}")
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            resp = requests.get(archive_url, headers=headers, timeout=config.URL_FETCH_TIMEOUT)
            if resp.status_code == 404:
                print(f"  Archive not found: {archive_url}")
                continue
            resp.raise_for_status()
            soup = BeautifulSoup(resp.content, 'html.parser')

            # Find story links on the monthly index
            for a in soup.find_all('a', href=True):
                href = a['href']
                abs_url = urljoin(archive_url, href)
                if 'news.emory.edu/stories/' not in abs_url:
                    continue
                if not abs_url.endswith('/story.html'):
                    continue
                if abs_url in processed_urls:
                    continue

                title = a.get_text(strip=True) or 'Untitled'

                # Try to extract date from slug; if missing, approximate to month start
                url_date = extract_date_from_url(abs_url)
                # If date is not found, fetch the date from child element(<div class="tag-list-item-meta">) of <a href="...">
                if url_date is None:
                    meta = a.find('div', class_='tag-list-item-meta')
                    if meta:
                        url_date = meta.get_text(strip=True)

                try:
                    ad = datetime.strptime(url_date, '%Y-%m-%d').date()
                    if ad < start_date or ad > end_date:
                        continue
                except ValueError:
                    pass

                found_articles.append({
                    'title': title,
                    'url': abs_url,
                    'snippet': title,
                    'url_date': url_date
                })
                processed_urls.add(abs_url)

        except requests.exceptions.RequestException as e:
            print(f"  Error accessing Emory archive {archive_url}: {e}")
        except Exception as e:
            print(f"  Error processing Emory archive {archive_url}: {e}")

    print(f"Emory monthly archives yielded {len(found_articles)} articles in range")
    return found_articles



def emory_scan_archive_pages_for_date_range() -> list[dict]:
    edu_articles = emory_scan_edu_pages_for_date_range()
    wheel_articles = emory_scan_wheel_pages_for_date_range()
    return edu_articles + wheel_articles