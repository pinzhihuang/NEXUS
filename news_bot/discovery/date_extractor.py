import re
from datetime import datetime


def extract_date_from_url(url_string: str) -> str | None:
    """
    Attempts to extract a date from a URL string.
    Looks for various date patterns commonly used in news URLs.
    """
    # Pattern for /news/YYYY/MM/DD/ (most common for NYU news)
    match_news_ymd = re.search(r'/news/(\d{4})/(\d{1,2})/(\d{1,2})/', url_string)
    if match_news_ymd:
        year, month, day = match_news_ymd.groups()
        try:
            dt = datetime(int(year), int(month), int(day))
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass
            
    # Match ..._DD-MM-YYYY/story.html (most common for Emory news)
    m = re.search(r'_(\d{2})-(\d{2})-(\d{4})/story\.html$', url_string)
    if m:
        day, month, year = m.groups()
        try:
            dt = datetime(int(year), int(month), int(day))
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            return None
        
    # Pattern for /YYYY/MM/DD/ (generic)
    match_ymd = re.search(r'/(\d{4})/(\d{1,2})/(\d{1,2})/', url_string)
    if match_ymd:
        year, month, day = match_ymd.groups()
        try:
            dt = datetime(int(year), int(month), int(day))
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass        
    return None
