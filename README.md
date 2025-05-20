# LIVE Weekly News Bot for NYU Chinese International Students

This project automates the process of discovering, verifying, and summarizing news relevant to Chinese international students at New York University.

## Features

-   **News Discovery**: Searches specified news sources (New York Times, Washington Square News, Official NYU websites) for relevant articles using the Perplexity API.
-   **Content Extraction**: Fetches and parses the full text content from discovered article URLs.
-   **AI-Powered Verification**: Uses Google's Gemini API (Flash model) to:
    -   Determine the publication date of articles.
    -   Verify if articles are recent (published within the last week).
    -   Assess relevance to the target audience.
    -   Check if the article appears to be a factual news report.
-   **AI-Powered Summarization**: Uses Google's Gemini API to generate concise, professional news summaries from verified articles.
-   **Structured Output**: Saves the final news reports in a JSON format.

## Project Structure

```
LIVE_WEEKLY_BOT/
├── news_bot/                   # Main application package
│   ├── __init__.py
│   ├── main_orchestrator.py    # Main script to run the workflow
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py           # Handles API keys, constants
│   │
│   ├── discovery/
│   │   ├── __init__.py
│   │   └── search_client.py    # Perplexity API for news search
│   │
│   ├── processing/
│   │   ├── __init__.py
│   │   └── article_handler.py  # URL fetching, Gemini for verification
│   │
│   ├── generation/
│   │   ├── __init__.py
│   │   └── summarizer.py       # Gemini for summarization
│   │
│   └── utils/
│       ├── __init__.py
│       └── file_manager.py     # Saving outputs
│
├── .env                        # Stores API keys (GEMINI_API_KEY, PERPLEXITY_API_KEY)
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
4.  **Set up API Keys**:
    Create a `.env` file in the `LIVE_WEEKLY_BOT` root directory and add your API keys:
    ```env
    GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
    PERPLEXITY_API_KEY="YOUR_PERPLEXITY_API_KEY"
    ```
    Replace `"YOUR_GEMINI_API_KEY"` and `"YOUR_PERPLEXITY_API_KEY"` with your actual keys.

## Usage

Run the main orchestrator script from the `LIVE_WEEKLY_BOT` root directory:

```bash
python -m news_bot.main_orchestrator
```

The script will process the news and save the results to a JSON file (e.g., `news_reports_YYYY-MM-DD.json`) in the project root or a designated output directory.

## Modules

-   **`config.py`**: Manages configuration settings, including API keys and search parameters.
-   **`search_client.py`**: Handles interactions with the Perplexity API to find news articles.
-   **`article_handler.py`**: Responsible for fetching content from URLs and using Gemini to verify articles for recency, relevance, and apparent factuality.
-   **`summarizer.py`**: Uses Gemini to generate summaries of verified articles.
-   **`file_manager.py`**: Provides utilities for saving data to files.
-   **`main_orchestrator.py`**: Coordinates the overall workflow from discovery to summarization and output.

## License

MIT License 