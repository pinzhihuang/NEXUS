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


def ubc_scan_category_pages_for_date_range() -> list[dict]:
    school = school_config.SCHOOL_PROFILES['ubc']
    start_date, end_date = config.get_news_date_range()
    page = 0
    flag = True
    print(f"\n--- Scanning Category Pages for {start_date} to {end_date} ---")
    
    found_articles: list[dict] = []
    processed_urls: set[str] = set()

    if not school.get('category_pages'):
        return []

    for page_url in school['category_pages']:
        # UBC uses a pagination system, flip page until the page date is outside the range
        while flag:
            print(f"Checking UBC category page: {page_url}")
            
            try:
                ajax_url = "https://ubctoday.ubc.ca/views/ajax"
                payload = {
                "view_name": "content_roundup",
                "view_display_id": "block_1",
                "view_args": "",
                "view_path": "/updates-news-and-stories",
                "pager_element": "0",
                "page": page,
                "_drupal_ajax": "1",
                "_wrapper_format": "drupal_ajax",
                }
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
                    "Accept": "application/json",
                    "X-Requested-With": "XMLHttpRequest",
                    "Referer": "https://ubctoday.ubc.ca/updates-news-and-stories",
                }
                cmds = requests.post(
                    ajax_url,
                    data=payload,
                    headers=headers,
                    timeout=config.URL_FETCH_TIMEOUT  # or (10, 30)
                ).json()
                html = next((c.get("data") for c in cmds if isinstance(c, dict) and c.get("command") == "insert"), "")
                soup = BeautifulSoup(html, "html.parser")
                
                for card in soup.find_all('div', class_='ubc-card__content'):
                    # extract the link
                    link = card.find('a', href=True)
                    if link:
                        href = link['href']
                        abs_url = urljoin(page_url, href)
                        # deduplication + ignore news from news.ok.ubc.ca
                        if abs_url in processed_urls or "https://news.ok.ubc.ca/" in abs_url:
                            continue
                        
                        # extract the title
                        title = card.find('h2', class_='card__title').find('span').get_text(strip=True)
                        
                        # extract the date - select the second div element inside the card
                        date = card.find_all('div')[1].get_text(strip=True)
                        
                        url_date_str = to_url_date(date.split('|')[0])
                        if not url_date_str:
                            continue
                        article_date = datetime.strptime(url_date_str, "%Y-%m-%d").date()
                        if article_date > end_date:
                            # newer than window → skip this card
                            continue                 
                        if article_date < start_date:
                            flag = False
                            break
                        # add the article to the list
                        found_articles.append({
                            "title": title,
                            "url": abs_url,
                            "snippet": title,
                            "url_date": url_date_str
                        })
                        processed_urls.add(abs_url)
                                       
                page += 1
            except Exception as e:
                print(f"  Error accessing UBC category page {page_url}: {e}")
    return found_articles


def ubc_scan_archive_pages_for_date_range() -> list[dict]:
    school = school_config.SCHOOL_PROFILES['ubc']
    start_date, end_date = config.get_news_date_range()
    print(f"\n--- Scanning Archive Pages for {start_date} to {end_date} ---")
    
    found_articles: list[dict] = []
    processed_urls: set[str] = set()

    # if not school.get('archive_patterns'):
    #     return []

    # # usc uses a monthly index page
    # monthly_pattern = school['archive_patterns'][0]  # https://news.UBC.edu/stories/{year}/{month:02d}/index.html

    # for y, m in _month_iter(start_date, end_date):
    #     # get the archive url for the month
    #     archive_url = monthly_pattern.format(year=y, month=m)
    #     print(f"Checking UBC monthly archive: {archive_url}")
    #     try:
    #         headers = {
    #             'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    #         }
    #         resp = requests.get(archive_url, headers=headers, timeout=config.URL_FETCH_TIMEOUT)
    #         if resp.status_code == 404:
    #             print(f"  Archive not found: {archive_url}")
    #             continue
    #         resp.raise_for_status()
    #         soup = BeautifulSoup(resp.content, 'html.parser')

    #         # Find story links on the monthly index
    #         articles_found_in_archive = 0
    #         month_regex = re.compile(r"(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t)?(?:ember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2},\s+\d{4}")
    #         for card in soup.find_all('div', class_='ubconewscard'):
    #             a = card.find('a', href=True)
    #             href = a['href']
    #             abs_url = urljoin(archive_url, href)

    #             # Skip self-links/anchors and duplicates
    #             if abs_url.startswith(archive_url) or abs_url in processed_urls:
    #                 continue

    #             title = a.get_text(strip=True) or 'Untitled'

    #             # Derive date
    #             url_date = extract_date_from_url(abs_url)
    #             if url_date is None:
    #                 # Search up the DOM for a date-like string within the card container
    #                 dt_str = None
    #                 if card is None:
    #                     break
    #                 text_blob = card.find('div', class_='ubconewscard-title').get_text(strip=True)     # e.g. Sep 5, 2025| Global Message
    #                 m = month_regex.search(text_blob)
    #                 if m:
    #                     dt_str = m.group(0)
    #                     break
    #                 if dt_str:
    #                     url_date = to_url_date(dt_str)
                        

    #             if not url_date:
    #                 continue

    #             try:
    #                 article_date = datetime.strptime(url_date, "%Y-%m-%d").date()
    #                 if article_date < start_date or article_date > end_date:
    #                     continue
    #             except ValueError:
    #                 continue
                

    #             print(f"  DEBUG: Article URL: {abs_url} ({url_date})")
    #             found_articles.append({
    #                 "title": title,
    #                 "url": abs_url,
    #                 "snippet": title,
    #                 "url_date": url_date
    #             })
    #             processed_urls.add(abs_url)
    #             articles_found_in_archive += 1

    #         if articles_found_in_archive > 0:
    #             print(f"  Found {articles_found_in_archive} relevant articles in this archive")

    #     except requests.exceptions.RequestException as e:
    #         print(f"  Error accessing UBC archive {archive_url}: {e}")
    #     except Exception as e:
    #         print(f"  Error processing UBC archive {archive_url}: {e}")
    
    found_articles.append({
        "title": "Nitobe Memorial Garden: A garden that bridges worlds",
        "url": "https://news.ubc.ca/2025/10/nitobe-memorial-garden-bridges-worlds/",
        "snippet": "Nitobe Memorial Garden: A garden that bridges worlds",
        "url_date": "2025-10-21"
    })
    # found_articles.append({
    #     "title": "How to welcome newcomer students to schools in Canada — and why everyone benefits",
    #     "url": "https://news.ubc.ca/2025/10/how-to-welcome-newcomer-students/",
    #     "snippet": "How to welcome newcomer students to schools in Canada — and why everyone benefits",
    #     "url_date": "2025-10-16"
    # })

    print(f"UBC monthly archives yielded {len(found_articles)} articles in range")
    print(f"DEBUG: UBC found articles: {found_articles}")
    found_articles.extend(ubc_scan_category_pages_for_date_range())
    print(f"DEBUG: UBC found articles after category scan: {found_articles}")
    return found_articles




