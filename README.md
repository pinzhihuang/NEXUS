# Project NEXUS - Student News 

Project NEXUS is an automated system for discovering, verifying, summarizing, and restyling news relevant to international students at various universities. It aims to provide a centralized and accessible source of important campus and community information.

## Features

-   **Configurable News Discovery**:
    -   Scans user-specified news category pages for the latest article links.
    -   Utilizes Google Programmable Search Engine (PSE) for targeted searches on user-configured university domains using relevant keywords.
-   **Content Extraction**: Fetches and parses the full text content from discovered article URLs.
-   **AI-Powered Verification (Gemini API)**:
    -   Determines the publication date of articles (from text and URL parsing).
    -   Verifies if articles are recent (based on a configurable threshold).
    -   Assesses relevance to the general student body of the configured university/community.
    -   Identifies the article type (e.g., "News article", "Opinion/Blog") to filter for news.
-   **News Summarization (Gemini API)**:
    -   Generates detailed yet concise English summaries (configurable length) focusing on key information.
-   **Restyling (Gemini API)**:
    -   Generates a relevant, catchy, and summary-style Chinese title for the news.
    -   Translates the English summary into Simplified Chinese.
    -   Rewrites the translation in a serious, formal, and objective news reporting style.
    -   Incorporates publication date and source attribution.
    -   Formats proper English names appropriately for Chinese readers.
-   **Structured Output**: Saves the final news reports (including English summary, Chinese title, and Chinese report) in a JSON format.

## Project Structure

```
NEXUS/  (Previously LIVE_WEEKLY_BOT)
├── news_bot/                   # Main application package
│   ├── __init__.py
│   ├── main_orchestrator.py    # Main script to run the workflow
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py           # API keys, constants, target URLs/keywords
│   │
│   ├── discovery/
│   │   ├── __init__.py
│   │   └── search_client.py    # Category page scanning & Google PSE client
│   │
│   ├── processing/
│   │   ├── __init__.py
│   │   └── article_handler.py  # URL fetching, Gemini for verification
│   │
│   ├── generation/
│   │   ├── __init__.py
│   │   └── summarizer.py       # Gemini for English summarization
│   │
│   ├── localization/
│   │   ├── __init__.py
│   │   └── translator.py       # Gemini for Chinese translation & title
│   │
│   └── utils/
│       ├── __init__.py
│       └── file_manager.py     # Saving outputs
│
├── .env.example                # Example environment file structure
├── requirements.txt            # Project dependencies
└── README.md                   # This file
```

## Setup

1.  **Clone the Repository** (if you haven't already):
    ```bash
    git clone <repository_url> NEXUS
    cd NEXUS
    ```
2.  **Create a Python Virtual Environment (recommended)**:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```
3.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
4.  **Set up API Keys & Configuration**:
    *   Create a `.env` file in the `NEXUS` root directory (you can copy `.env.example` if provided and rename it).
    *   Populate your `.env` file with the necessary API keys:
        ```env
        GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
        GOOGLE_API_KEY="YOUR_GOOGLE_API_KEY"
        CUSTOM_SEARCH_ENGINE_ID="YOUR_GOOGLE_PSE_CX_ID"
        # PERPLEXITY_API_KEY="YOUR_PERPLEXITY_API_KEY" # If using any Perplexity features
        
        # Optional: Override default model names or parameters from config.py
        # GEMINI_FLASH_MODEL='gemini-1.5-flash-latest'
        # RECENCY_THRESHOLD_DAYS=7 
        ```
    *   **Google Programmable Search Engine (PSE) Setup**:
        1.  Create/select a project in [Google Cloud Console](https://console.cloud.google.com/).
        2.  Enable the "Custom Search API" in the API Library.
        3.  Create an API Key in "APIs & Services" > "Credentials" and restrict it to the "Custom Search API". This is your `GOOGLE_API_KEY`.
        4.  Go to the [Programmable Search Engine control panel](https://programmablesearchengine.google.com/).
        5.  Create a new search engine. In its setup, under "Sites to search", add the specific university news domains you want to target (e.g., `news.exampleuniversity.edu/*`, `students.exampleuniversity.edu/events/*`). This is crucial for targeting.
        6.  Note its "Search engine ID (CX)" for your `CUSTOM_SEARCH_ENGINE_ID` in the `.env` file.
    *   **Configure `news_bot/core/config.py` (or use `.env` overrides)**:
        *   Review and update `TARGET_NEWS_SOURCES_DOMAINS` to include the primary domains of the universities you are targeting.
        *   Update `CATEGORY_PAGES_TO_SCAN` with specific news category/archive URLs from your target university sites that you want to scan directly.
        *   Adjust `RELEVANCE_KEYWORDS` to suit the general student population of the target universities and the type of news you're interested in. The summarization and translation prompts can further tailor content for specific international student groups if needed.

## Usage

Run the main orchestrator script from the `NEXUS` root directory:

```bash
python -m news_bot.main_orchestrator
```

The script will process news based on your configuration and save the results to a JSON file (e.g., `news_reports/weekly_news_report_YYYY-MM-DD_HHMMSS.json`) in the output directory specified in `config.py` (default is `news_reports`).

## Modules

-   **`config.py`**: Manages configuration: API keys, model names, target university news domains and category pages, relevance keywords, output settings. Many settings can be overridden via `.env`.
-   **`search_client.py`**: Discovers news by scanning specified category pages and querying Google Programmable Search Engine.
-   **`article_handler.py`**: Fetches article text and uses Gemini for verification (date, recency, relevance, article type).
-   **`summarizer.py`**: Generates detailed English summaries using Gemini.
-   **`translator.py`**: Translates English summaries into formal Chinese news reports, generates Chinese titles, and formats names, using Gemini.
-   **`file_manager.py`**: Saves structured data to JSON files.
-   **`main_orchestrator.py`**: Coordinates the end-to-end workflow.

## Customization for a New University

1.  **Google PSE**: Update your Google Programmable Search Engine to include the new university's news domains.
2.  **`.env` / `config.py`**: 
    *   Modify `TARGET_NEWS_SOURCES_DOMAINS` in `config.py`.
    *   Add relevant `CATEGORY_PAGES_TO_SCAN` for the new university in `config.py`.
    *   Adjust `RELEVANCE_KEYWORDS` if the focus shifts significantly.
3.  **Prompts (Optional)**: If targeting a vastly different student demographic or news style, you might review and tweak the prompts in `article_handler.py`, `summarizer.py`, and `translator.py`.
