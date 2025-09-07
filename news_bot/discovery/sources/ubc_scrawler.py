import re
from datetime import datetime, date
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from ...discovery.date_extractor import extract_date_from_url
from ...core import config, school_config


def to_url_date(dt_str: str) -> str | None:
    if not dt_str:
        return None
    s = dt_str.strip().replace('\u00a0', ' ')  # normalize whitespace
    s = re.sub(r'(?<=\\s)(\\d{1,2})(st|nd|rd|th)', r'\\1', s)  # remove ordinals like 5th
    print(f"  DEBUG: UBC Date String: {s}")
    for fmt in ("%b %d, %Y", "%B %d, %Y"):  # Sep / September
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


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


def ubc_scan_archive_pages_for_date_range() -> list[dict]:
    school = school_config.SCHOOL_PROFILES['ubc']
    start_date, end_date = config.get_news_date_range()
    print(f"\n--- Scanning Archive Pages for {start_date} to {end_date} ---")
    
    found_articles: list[dict] = []
    processed_urls: set[str] = set()

    if not school.get('archive_patterns'):
        return []

    # usc uses a monthly index page
    monthly_pattern = school['archive_patterns'][0]  # https://news.UBC.edu/stories/{year}/{month:02d}/index.html

    for y, m in _month_iter(start_date, end_date):
        # get the archive url for the month
        archive_url = monthly_pattern.format(year=y, month=m)
        print(f"Checking UBC monthly archive: {archive_url}")
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
            articles_found_in_archive = 0
            month_regex = re.compile(r"(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t)?(?:ember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2},\s+\d{4}")
            for card in soup.find_all('div', class_='ubconewscard'):
                a = card.find('a', href=True)
                href = a['href']
                abs_url = urljoin(archive_url, href)

                # Skip self-links/anchors and duplicates
                if abs_url.startswith(archive_url) or abs_url in processed_urls:
                    continue

                title = a.get_text(strip=True) or 'Untitled'

                # Derive date
                url_date = extract_date_from_url(abs_url)
                if url_date is None:
                    # Search up the DOM for a date-like string within the card container
                    dt_str = None
                    if card is None:
                        break
                    text_blob = card.find('div', class_='ubconewscard-title').get_text(strip=True)     # e.g. Sep 5, 2025| Global Message
                    m = month_regex.search(text_blob)
                    if m:
                        dt_str = m.group(0)
                        break
                    if dt_str:
                        url_date = to_url_date(dt_str)
                        

                if not url_date:
                    continue

                try:
                    article_date = datetime.strptime(url_date, "%Y-%m-%d").date()
                    if article_date < start_date or article_date > end_date:
                        continue
                except ValueError:
                    continue
                

                print(f"  DEBUG: Article URL: {abs_url} ({url_date})")
                found_articles.append({
                    "title": title,
                    "url": abs_url,
                    "snippet": title,
                    "url_date": url_date
                })
                processed_urls.add(abs_url)
                articles_found_in_archive += 1

            if articles_found_in_archive > 0:
                print(f"  Found {articles_found_in_archive} relevant articles in this archive")

        except requests.exceptions.RequestException as e:
            print(f"  Error accessing UBC archive {archive_url}: {e}")
        except Exception as e:
            print(f"  Error processing UBC archive {archive_url}: {e}")

    print(f"UBC monthly archives yielded {len(found_articles)} articles in range")
    return found_articles




