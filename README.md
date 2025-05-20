# LIVE Weekly News Bot for NYU Chinese International Students

This project automates the process of discovering, verifying, summarizing, and translating news relevant to Chinese international students at New York University.

## Features

-   **Hybrid News Discovery**:
    -   Scans specific news category pages (e.g., WSN news section) for the latest article links.
    -   Utilizes Google Programmable Search Engine (PSE) for targeted searches on configured domains (e.g., `www.nyu.edu/news`) using relevant keywords.
-   **Content Extraction**: Fetches and parses the full text content from discovered article URLs.
-   **AI-Powered Verification (Gemini Flash)**:
    -   Determines the publication date of articles.
    -   Verifies if articles are recent (published within the configured threshold, typically the last week).
    -   Assesses relevance to the target audience (Chinese international students at NYU).
    -   Identifies the article type (e.g., "News article", "Opinion/Blog") to ensure only news is processed.
-   **AI-Powered English Summarization (Gemini Flash)**:
    -   Generates detailed yet concise English summaries (approx. 5-7 sentences, 100-180 words) focusing on key information (who, what, when, where, implications, key stats).
-   **AI-Powered Chinese Translation & Restyling (Gemini Flash)**:
    -   Generates a relevant, catchy, and summary-style Chinese title for the news.
    -   Translates the English summary into Simplified Chinese.
    -   Rewrites the translation in a serious, formal, and objective news reporting style.
    -   Incorporates publication date and source attribution (e.g., "据WSN报道，YYYY-MM-DD消息：").
    -   Formats proper English names: "中文译名 (Original English Name)" for less common names, while using direct Chinese translation for highly popular names (e.g., NYU, Trump).
-   **Structured Output**: Saves the final news reports (including English summary, Chinese title, and Chinese report) in a JSON format, timestamped by run date.

## Project Structure

```
LIVE_WEEKLY_BOT/
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
├── .env                        # Stores API keys
├── requirements.txt            # Project dependencies
└── README.md                   # This file
```

## Setup

1.  **Clone the repository (if applicable)**
2.  **Create a Python virtual environment (recommended)**:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```
3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
4.  **Set up API Keys & Google PSE**:
    *   Create a `.env` file in the `LIVE_WEEKLY_BOT` root directory:
        ```env
        GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
        GOOGLE_API_KEY="YOUR_GOOGLE_API_KEY"
        CUSTOM_SEARCH_ENGINE_ID="YOUR_GOOGLE_PSE_CX_ID"
        # PERPLEXITY_API_KEY="YOUR_PERPLEXITY_API_KEY" # If still using Perplexity parts
        ```
    *   **Google Programmable Search Engine (PSE)**:
        1.  Create/select a project in [Google Cloud Console](https://console.cloud.google.com/).
        2.  Enable the "Custom Search API" in the API Library.
        3.  Create an API Key in "APIs & Services" > "Credentials" and restrict it to the "Custom Search API". This is your `GOOGLE_API_KEY`.
        4.  Go to the [Programmable Search Engine control panel](https://programmablesearchengine.google.com/).
        5.  Create a new search engine. In its setup, under "Sites to search", add the domains you want Google PSE to cover (e.g., `www.nyu.edu/news/*`). Note its "Search engine ID (CX)" for `CUSTOM_SEARCH_ENGINE_ID`.

## Usage

Run the main orchestrator script from the `LIVE_WEEKLY_BOT` root directory:

```bash
python -m news_bot.main_orchestrator
```

The script will process the news and save the results to a JSON file (e.g., `news_reports/weekly_news_report_YYYY-MM-DD.json`).

## Modules

-   **`config.py`**: Manages configuration: API keys, Gemini model names, target category page URLs, Google PSE domains, relevance keywords, output settings.
-   **`search_client.py`**: Handles news discovery by scanning specified category pages (e.g., WSN) and querying Google Programmable Search Engine for other configured sites.
-   **`article_handler.py`**: Fetches full article text from URLs and uses Gemini for verification (date, recency, relevance, article type).
-   **`summarizer.py`**: Generates detailed English summaries of verified articles using Gemini.
-   **`translator.py`**: Translates English summaries into formal Chinese news reports, generates Chinese titles, and formats names, using Gemini.
-   **`file_manager.py`**: Saves the final structured data (including English and Chinese content) to JSON files.
-   **`main_orchestrator.py`**: Coordinates the entire workflow, from discovery through processing, generation, translation, and saving.

## License

MIT License 