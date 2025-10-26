SCHOOL_PROFILES = {
  "nyu": {
    "id": 1,
    "school_name": "New York University (NYU)",
    "school_location": "New York",
    "domains": ["nyunews.com", "www.nyu.edu/news"],                    #  limit discoveries to allowed hostnames.
    "category_pages": ["https://nyunews.com/category/news/"],          #  Seed URLs for listing pages to crawl for article links.
    "archive_patterns": [
      "https://nyunews.com/{year}/{month:02d}/",
      "https://www.nyu.edu/about/news-publications/news/{year}/{month:02d}.html",
      "https://nyunews.com/news/{year}/{month:02d}/",
    ],
    "validators": [r"/news/\d{4}/\d{2}/\d{2}/"],
    "selectors": {},  # site-specific main content selectors if needed
    "pse_sites": ["nyunews.com", "nyu.edu"],
    "prompt_context": {
      "audience_en": "Chinese international students at New York University (NYU)",
      "audience_zh": "纽约大学（NYU）的中国留学生",
    },
    "relevance_keywords": ["Chinese international students","NYU","New York student life","campus events"]
  },
  "emory": {
    "id": 2,
    "school_name": "Emory University",
    "school_location": "Atlanta",
    "domains": ["news.emory.edu", "www.emorywheel.com"],
    "category_pages": [
      # Monthly and root index are handled by emory_crawler; keep for completeness
      "https://news.emory.edu/stories/index.html",
      "https://www.emorywheel.com/section/news"
    ],
    "archive_patterns": [
      # Emory monthly index pages
      "https://news.emory.edu/stories/{year}/{month:02d}/",
    ],
    "validators": [
      # Emory story detail URLs under a monthly path
      r"^https?://news\.emory\.edu/stories/\d{4}/\d{2}/[^/]+/story\.html$",
      # Optional: slug-embedded date like _DD-MM-YYYY
      r"_(\d{2})-(\d{2})-(\d{4})/story\.html$"
    ],
    "selectors": {},
    "pse_sites": ["news.emory.edu", "emorywheel.com"],
    "prompt_context": {
      "audience_en": "Chinese international students at Emory University",
      "audience_zh": "埃默里大学的中国留学生",
    },
    "relevance_keywords": ["Emory University","Atlanta campus","students","international students","DEI at Emory"]
  },
  "ucd": {
    "id": 3,
    "school_name": "University of California, Davis",
    "school_location": "Davis",
    "domains": ["www.ucdavis.edu", "theaggie.org"],
    "category_pages": ["https://www.ucdavis.edu/news/latest"],
    "archive_patterns": [
      # USC monthly index pages
      "https://news.emory.edu/stories/{year}/{month:02d}/",
    ],
    "validators": [r"/\d{4}/\d{2}/\d{2}/", r"/news/"],
    "selectors": {},
    "pse_sites": ["ucdavis.edu", "theaggie.org"],
    "prompt_context": {
      "audience_en": "Chinese international students at UC Davis",
      "audience_zh": "加州大学戴维斯分校的中国留学生",
    },
    "relevance_keywords": ["UC Davis","Davis campus","students","international students"]
  },
  "ubc": {
    "id": 4,
    "school_name": "University of British Columbia",
    "school_location": "Vancouver",
    "domains": ["news.ubc.ca", "ubctoday.ubc.ca", "ubyssey.ca"],
    "category_pages": [
      "https://ubctoday.ubc.ca/updates-news-and-stories",
      "https://news.ubc.ca/category/university-news/",
    ],
    "archive_patterns": [
      
      ],
    "validators": [r"/\d{4}/\d{2}/\d{2}/", r"/news/"],
    "selectors": {},
    "pse_sites": ["news.ubc.ca", "ubctoday.ubc.ca", "ubyssey.ca"],
    "prompt_context": {
      "audience_en": "Chinese international students at UBC",
      "audience_zh": "英属哥伦比亚大学的中国留学生",
    },
    "relevance_keywords": ["UBC","Vancouver campus","students","international students"],
    "include_event_announcements": True
  },
  "usc": {
    "id": 5,
    "school_name": "University of Southern California",
    "school_location": "Los Angeles",
    "domains": ["news.usc.edu", "usc.edu"],
    "category_pages": ["https://www.uscannenbergmedia.com/pf/api/v3/content/fetch/story-feed-query"],
    "archive_patterns": [
      "https://www.uscannenbergmedia.com/allnews/",
    ],
    "validators": [r"/\d{4}/\d{2}/\d{2}/", r"/news/"],
    "selectors": {},
    "pse_sites": ["uscannenbergmedia.com"],
    "prompt_context": {
      "audience_en": "Chinese international students at USC",
      "audience_zh": "南加州大学的中国留学生",
    },
    "relevance_keywords": ["USC","Los Angeles campus","students","international students"]
  },
  "edin": {
    "id": 6,
    "school_name": "University of Edinburgh",
    "school_location": "Edinburgh",
    "domains": ["www.ed.ac.uk", "www.ed.ac.uk/news"],
    "category_pages": ["https://www.ed.ac.uk/news/latest?search_api_news_fulltext=&field_news_publication_date%5Bmin%5D={start_year}-{start_month:02d}-{start_day:02d}&field_news_publication_date%5Bmax%5D={end_year}-{end_month:02d}-{end_day:02d}",
                       "https://thestudentnews.co.uk/category/news/"],
    "archive_patterns": [
      ],
    "validators": [r"/\d{4}/\d{2}/\d{2}/", r"/news/"],
    "selectors": {},
    "pse_sites": ["ed.ac.uk"],
    "prompt_context": {
      "audience_en": "Chinese international students at Edinburgh",
      "audience_zh": "爱丁堡大学的中国留学生",
    },
    "relevance_keywords": ["Edinburgh","Edinburgh campus","students","international students"],
    "include_opinion_blog": True
  }
}