# Project NEXUS - Student News 

Project NEXUS is an automated system for discovering, verifying, summarizing, and translating news relevant to international students at various universities. It aims to provide a centralized and accessible source of important campus and community information.

## Feature Log

[2025-12-20]
- **Enhanced Rendering & Image Logic**:
  - **Smart Image Discovery**: Automatically fetches cover images from source URLs (meta tags) if no inline image exists in the Google Doc.
  - **`--no-images` Mode**: New flag to skip all image extraction/fetching for faster text-only rendering.
- **Automation & Robustness**:
  - **Flexible Date Parsing**: Master Doc now supports multiple date formats (e.g., `YYYY.MM.DD - YYYY.MM.DD`) and performs logical date range matching.
- **Shell & CLI Updates**:
  - **Extended Wrappers**: `render_single_doc.sh` now supports passing `no-images` as an argument.
  - **Parameter Support**: Python scripts now accept `--body-size` and `--no-images` as command-line arguments.
    
[2025-10-29]
- Google Docs → WeChat news renderer landed:
  - **Batch renderer** `scripts/gdoc_master_latest_to_images.py` (parse master weekly index; batch render per-school docs).
  - **Single-doc renderer** `scripts/gdoc_to_wechat_images.py` (render one school/week).
  - **Week selector**: `--week-title "YYYY.MM.DD - MM.DD"`; default picks the latest week.
  - **Robust link parsing**: supports Smart Chips (richLink), links inside **paragraphs / tables / TOC**, and inlineObject rich links.
  - **DocId normalization & de-dup** to avoid missing/duplicated schools.
  - **UCD special styling**: alternating left bar (blue/yellow) by odd/even items.
- HTML templates & font:
  - `news_bot/templates/weixin_article_template.html`
  - `news_bot/templates/weixin_reference_template.html`
  - `news_bot/assets/fonts/SourceHanSerifSC-VF.otf` (large file; consider Git LFS).
- One-click shell wrappers:
  - `scripts/render_latest_week.sh` – render **latest** week for all schools.
  - `scripts/render_week.sh` – render **latest** or an **exact** week.
  - `scripts/render_single_doc.sh` – render **one** school doc by URL/ID.
- Docs:
  - Added **render_readme.md** (setup, OAuth, CLI examples, troubleshooting).

[2025-10-12]
- A bash script added for running extracting news from 6 schools all at once.

[2025-10-03]

- Add University of Edinburgh as a new source.
  - New crawler `news_bot/discovery/sources/edin_scrawler.py` and profile in `news_bot/core/school_config.py`.
  - Supports Edinburgh official news page with date-range query and student newspaper.
- Security/housekeeping: stop tracking leaked Gmail OAuth token files and ignore them.

[2025-09-07]

- Enable Event/Announcement summaries for UBC when configured.
  - Added per-school flag `include_event_announcements` in `news_bot/core/school_config.py` (enabled for UBC).
  - Updated `news_bot/main_orchestrator.py` suitability logic to accept `Event/Announcement` when the flag is true.

[2025-09-06]

- UC Davis support completed.
  - Implement `ucd_scan_category_pages_for_links` to crawl latest news and filter by configured date range.
  - Add UC Davis profile to `news_bot/core/school_config.py`.

[2025-09-05]

- Emory support finished.
  - Implement combined scanners for Emory official news monthly index and Emory Wheel pages with date filtering.
  - Add Emory profile to `news_bot/core/school_config.py`.

[2025-09-04]
- Improved translation prompt, Gemini refinement, and ranking by relevance.

[2025-08-20] 
- Custom Date Range Support: Added ability to specify a custom start date for news collection with 7-day window
    - New config: NEWS_START_DATE - Set any date as the starting point for news collection
    - Default: Current date minus 7 days (captures last week's news)
    - Format: YYYY-MM-DD in .env file or config.py
- Added specific URL pattern validation for news article and archive page scanning for precise date targeting
- Improved article discovery with multi-page category scanning
    - New config: MAX_CATEGORY_PAGES_TO_SCAN - Maximum number of category pages to scan for news sourcing

## Features

-   **Configurable News Discovery**:
    -   Scans user-specified news category pages for the latest article links.
    -   Utilizes Google Programmable Search Engine (PSE) for targeted searches on user-configured university domains using relevant keywords.
-   **Content Extraction**: Fetches and parses the full text content from discovered article URLs.
-   **AI-Powered Verification (OpenRouter with Gemini models)**:
    -   Determines publication dates (from text and URL parsing).
    -   Verifies article recency based on a configurable threshold.
    -   Assesses relevance to the general student body of the configured university/community.
    -   Identifies the article type (e.g., "News article", "Opinion/Blog") to filter for news.
-   **News Summarization (OpenRouter with Gemini models)**:
    -   Generates detailed yet concise English summaries (configurable length) focusing on key information.
-   **Restyling (OpenRouter with Gemini models)**:
    -   Generates a relevant, catchy, and summary-style Chinese title for the news.
    -   Translates the English summary into Simplified Chinese.
    -   Rewrites the translation in a serious, formal, and objective news reporting style.
    -   Incorporates publication date and source attribution.
    -   Formats English names appropriately for Chinese readers.
    -   Includes an additional AI-powered refinement step for the Chinese news report to improve conciseness and logical flow.
-   **Structured Output & Export**:
    -   Saves final news reports (English summary, Chinese title, initial Chinese report, refined Chinese report) to a timestamped JSON file.
    -   Exports the refined Chinese news reports to a Google Document:

## Project Structure

```
NEXUS/
├── news_bot/                   # Main application package
│   ├── __init__.py
│   ├── main_orchestrator.py    # Main script
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py           # Configuration, API keys, targets
│   ├── discovery/
│   │   ├── __init__.py
│   │   └── search_client.py    # News discovery (category scan, Google PSE)
│   ├── processing/
│   │   ├── __init__.py
│   │   └── article_handler.py  # Text extraction, Gemini verification
│   ├── generation/
│   │   ├── __init__.py
│   │   └── summarizer.py       # English summarization
│   ├── localization/
│   │   ├── __init__.py
│   │   └── translator.py       # Chinese translation, title, refinement
│   ├── reporting/
│   │   ├── __init__.py
│   │   └── google_docs_exporter.py # Google Docs export
│   └── utils/
│       ├── __init__.py
│       └── file_manager.py     # JSON saving utility
│
├── .env.example                # Example environment file
├── requirements.txt            # Dependencies
└── README.md                   # This file
```

## Setup

1.  **Clone Repository & Navigate**: 
    ```bash
    git clone <repository_url> NEXUS
    cd NEXUS
    ```
2.  **Virtual Environment (Recommended)**:
    ```bash
    python -m venv venv
    source venv/bin/activate  # Windows: venv\Scripts\activate
    ```
3.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
4.  **API Keys & Configuration (`.env` file)**:
    *   Create a `.env` file in the `NEXUS` root.
    *   Add your API keys:
        ```env
        # Required: OpenRouter API Key (get from https://openrouter.ai/keys)
        OPENROUTER_API_KEY="sk-or-v1-YOUR_OPENROUTER_API_KEY"
        
        # Optional: Google PSE keys (for custom search, currently disabled)
        # GOOGLE_API_KEY="YOUR_GOOGLE_API_KEY_FOR_PSE"
        # CUSTOM_SEARCH_ENGINE_ID="YOUR_GOOGLE_PSE_CX_ID"
        
        # Optional: For Google Docs Export - ID of an existing Doc to update
        # TARGET_GOOGLE_DOC_ID="YOUR_GOOGLE_DOCUMENT_ID_HERE"
        
        # Optional: Override default model names or parameters from config.py
        # GEMINI_FLASH_MODEL="google/gemini-2.5-flash"
        # GEMINI_PRO_MODEL="google/gemini-2.5-pro"
        # RECENCY_THRESHOLD_DAYS=7
        # NEWS_START_DATE="2025-08-01"
        # MAX_CATEGORY_PAGES_TO_SCAN=20
        ```
    *   **OpenRouter Setup**:
        1.  Go to https://openrouter.ai/ and create an account
        2.  Navigate to https://openrouter.ai/keys and create an API key
        3.  Add credits to your account at https://openrouter.ai/settings/credits (free tier includes some credits)
        4.  Copy your API key and add it to `.env` as `OPENROUTER_API_KEY`
    *   **Google Programmable Search Engine (PSE) Setup**:
        1.  Project in [Google Cloud Console](https://console.cloud.google.com/).
        2.  Enable "Custom Search API".
        3.  Create API Key (this is `GOOGLE_API_KEY`), restrict to "Custom Search API".
        4.  Create PSE at [Programmable Search Engine](https://programmablesearchengine.google.com/), configure sites to search, get Search Engine ID (`CUSTOM_SEARCH_ENGINE_ID`).
    *   **Google Docs API Setup (for Docs Export)**:
        1.  In the same Google Cloud Project, enable "Google Docs API".
        2.  Create OAuth 2.0 Client ID (Type: Desktop app) under "Credentials".
        3.  Download the client secret JSON file, rename it to `credentials.json` (or as specified in `config.OAUTH_CREDENTIALS_FILENAME`), and place it in the project root.
5.  **Target Configuration (`news_bot/core/config.py`)**: 
    *   Review/update `TARGET_NEWS_SOURCES_DOMAINS`, `CATEGORY_PAGES_TO_SCAN`, and `RELEVANCE_KEYWORDS` to suit your target university/community.

## Usage

Run the main script from the `NEXUS` root directory:
```bash
python -m news_bot.main_orchestrator
```
-   On the first run involving Google Docs export, a browser window will open for OAuth 2.0 authorization. You'll need to sign in and grant permissions.
-   Output JSON files will be saved in the directory specified by `DEFAULT_OUTPUT_DIR` in `config.py` (default: `news_reports`).
-   If Google Docs export is successful, the URL of the created/updated document will be printed in the console.

After running the main script, to rank the news by revelance, run coordinator.py from the `NEXUS` root directory:

```bash
python -m news_bot.processing.coordinator
```

For extracting news from all six school at once:
```bash
chmod +x /<your_path_to_NEXUS>/run_nexus_automation.sh

<your_path_to_NEXUS>/run_nexus_automation.sh
# or using the command below in case pc display off
caffeinate -i <your_path_to_NEXUS>/run_nexus_automation.sh 
```

## Modules

-   **`config.py`**: Manages all configurations (API keys, model names, target URLs, keywords, paths, etc.). Many can be overridden by `.env` variables.
-   **`search_client.py`**: Discovers news articles by scanning category pages and querying Google PSE.
-   **`article_handler.py`**: Fetches article text from URLs; uses OpenRouter (Gemini models) for verification (date, recency, relevance, article type).
-   **`summarizer.py`**: Generates detailed English summaries of verified articles using OpenRouter (Gemini models).
-   **`translator.py`**: Translates English summaries to formal Chinese news reports, generates Chinese titles, refines Chinese text, and formats names, using OpenRouter (Gemini models).
-   **`reporting/google_docs_exporter.py`**: Handles authentication and export of refined Chinese news reports to a Google Document (updates existing or creates new).
-   **`utils/file_manager.py`**: Saves structured data to JSON files.
-   **`main_orchestrator.py`**: Orchestrates the entire workflow.

## Customization for a New University

1.  **Google PSE**: Update your Google Programmable Search Engine settings to include the new university's specific news domains.
2.  **`.env` / `config.py`**: 
    *   Modify `TARGET_NEWS_SOURCES_DOMAINS` in `config.py`.
    *   Add relevant `CATEGORY_PAGES_TO_SCAN` for the new university in `config.py`.
    *   Adjust `RELEVANCE_KEYWORDS`.
    *   Optionally set `TARGET_GOOGLE_DOC_ID` in `.env` if you want to update a specific doc for this new university.
3.  **Prompts (Optional)**: For significantly different target audiences or news styles, review and tweak prompts in `article_handler.py`, `summarizer.py`, and `translator.py`.
