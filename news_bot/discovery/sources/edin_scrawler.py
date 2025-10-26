import re
from datetime import datetime, date, timedelta
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from ...discovery.date_extractor import extract_ymd_from_text, extract_date_from_url
from ...core import config, school_config

school = school_config.SCHOOL_PROFILES['edin']

def edin_scan_edinburgh_news_pages_for_date_range() -> list[dict]:
    start_date, end_date = config.get_news_date_range()
    print(f"\n--- Scanning Category Pages for {start_date} to {end_date} ---")
    
    found_articles: list[dict] = []
    processed_urls: set[str] = set()
    
    if not school.get('category_pages'):
        return []
    
    # Official Edinburgh News Page with date range specified in the url
    page_url = school['category_pages'][0].format(
        start_year=start_date.year, start_month=start_date.month, start_day=start_date.day,
        end_year=end_date.year,   end_month=end_date.month,   end_day=end_date.day
    )
    print(f"  Checking Edinburgh category page: {page_url}")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        resp = requests.get(page_url, headers=headers, timeout=config.URL_FETCH_TIMEOUT)
        if resp.status_code == 404:
            print(f"  Archive not found: {page_url}")
            return []
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, 'html.parser')
        cards = soup.find_all('div', class_='news-listing')
        for card in cards:
            a = card.find('a', href=True)
            href = a['href']
            abs_url = urljoin(page_url, href)
            title = a.get_text(strip=True) or 'Untitled'
            card_date = card.find('span', class_='news-date').get_text(strip=True)
            url_date = extract_ymd_from_text(card_date)
            if url_date is None:
                continue
            article_date = datetime.strptime(url_date, "%Y-%m-%d").date()
            if article_date >= start_date and article_date <= end_date:
                found_articles.append({
                    "url": abs_url,
                    "title": title,
                    "url_date": url_date
                })
                processed_urls.add(abs_url)
    except Exception as e:
        print(f"  Error accessing Edinburgh category page {page_url}: {e}")
    return found_articles

def edin_scan_thestudent_news_pages_for_date_range() -> list[dict]:
    start_date, end_date = config.get_news_date_range()
    print(f"\n--- Scanning The Student News Pages for {start_date} to {end_date} ---")
    
    found_articles: list[dict] = []
    processed_urls: set[str] = set()
    
    page_url = school['category_pages'][1]
    page_count = 0
    max_pages = 30
    flag = True
    
    try:
        # the first page is static, so we don't need to fetch it by AJAX
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(page_url, headers=headers, timeout=config.URL_FETCH_TIMEOUT)
        
        if response.status_code == 404:
            print(f"  Archive page not found: {page_url}")
            return []
        
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        for link in soup.find('div', class_='zeen-col--wide').find_all('a', href=True):
            href = link['href']
            abs_url = urljoin(page_url, href)
            
            if abs_url in processed_urls:
                continue
            # Filter out non-article URLs
            skip_patterns = [
                "/staff_name/", "/staff/", "/writer/", "/contributor/",
                "/category/news/", "/tag/", "/author/", "/page/",
                "/about/", "/contact/", "/privacy/", "/terms/",
                "#", "javascript:", "mailto:"
            ]
            if any(skip_path in abs_url.lower() for skip_path in skip_patterns):
                continue
                                
            # Chect if the a element has a text content as title
            if not link.get_text(strip=True):
                continue
            title = link.get_text(strip=True) or 'Untitled'
            
            url_date = extract_date_from_url(abs_url)
            if url_date is None:
                continue
            
            article_date = datetime.strptime(url_date, "%Y-%m-%d").date()
            if article_date >= start_date and article_date <= end_date:
                found_articles.append({
                    "url": abs_url,
                    "title": title,
                    "url_date": url_date
                })
                processed_urls.add(abs_url)
                
    except Exception as e:
        print(f"  Error accessing The Student News page {page_url}: {e}")
         
    return found_articles

    
def edin_scan_category_pages_for_date_range() -> list[dict]:
    return edin_scan_edinburgh_news_pages_for_date_range() + edin_scan_thestudent_news_pages_for_date_range()