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


def extract_ymd_from_text(date_string: str) -> str | None:
    """
    Parse a human-readable date string and return it as YYYY-MM-DD.

    Examples accepted:
      - "Tuesday, March 4, 2025"
      - "March 4, 2025"
      - "Mar 4, 2025"
      - "March 4th, 2025" (ordinal suffixes handled)
      - "25 September, 2025"

    Returns None if no supported format matches.
    """
    if not date_string:
        return None

    # Normalize whitespace and remove ordinal suffixes (1st, 2nd, 3rd, 4th)
    s = re.sub(r"\s+", " ", str(date_string).strip())
    s = re.sub(r"(\d{1,2})(st|nd|rd|th)", r"\1", s, flags=re.IGNORECASE)

    # Normalize month abbreviations with trailing periods and edge case "Sept"
    # Remove dots from common month abbreviations like "Mar.", "Aug.", etc.
    s = re.sub(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.\b", r"\1", s)
    # Map non-standard "Sept" to standard "Sep" expected by %b
    s = re.sub(r"\bSept\b", "Sep", s)

    # Try common formats from most to least specific
    candidate_formats = [
        "%A, %B %d, %Y",   # Tuesday, March 4, 2025
        "%A, %b %d, %Y",   # Tuesday, Mar 4, 2025
        "%A, %b. %d, %Y",   # Tuesday, Mar. 4, 2025
        "%B %d, %Y",       # March 4, 2025
        "%b %d, %Y",       # Mar 4, 2025
        "%d %B, %Y",        # 4 September, 2025
        "%Y-%m-%d",        # Already normalized
    ]

    for fmt in candidate_formats:
        try:
            dt = datetime.strptime(s, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue

    # If the string contains leading text like "Updated on ...", try last comma segment
    if "," in s:
        tail = s.split(",", maxsplit=1)[-1].strip()
        for fmt in ["%B %d, %Y", "%b %d, %Y"]:
            try:
                dt = datetime.strptime(tail, fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                pass

    return None