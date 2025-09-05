import re
from datetime import datetime, date, timedelta
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from ...discovery.date_extractor import extract_date_from_url
from ...core import config, school_config


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


def emory_scan_archive_pages_for_date_range() -> list[dict]:
    school = school_config.SCHOOL_PROFILES['emory']
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




