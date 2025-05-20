# news_bot/main_orchestrator.py

from datetime import datetime

from .core import config
from .discovery import search_client
from .processing import article_handler
from .generation import summarizer
from .utils import file_manager

def run_news_bot():
    """
    Main function to run the complete news bot workflow:
    1. Discover articles.
    2. For each article:
        a. Fetch and extract text.
        b. Verify for recency, relevance, and if it IS a news article.
        c. If verified, generate a summary.
    3. Save the compiled news reports.
    """
    print("===========================================")
    print("=== LIVE Weekly News Bot - Starting Run ===")
    print(f"=== Run timestamp: {datetime.now().isoformat()} ===")
    print("===========================================")

    # Validate configuration first
    try:
        config.validate_config()
        print("API keys and configuration successfully validated.")
    except ValueError as e:
        print(f"Configuration Error: {e}")
        print("Please ensure your .env file is correctly set up in the project root.")
        print("Bot run aborted due to configuration error.")
        return

    # Step 1: Discover articles
    print("\n--- Step 1: Discovering Articles ---")
    discovered_articles = search_client.find_relevant_articles()

    if not discovered_articles:
        print("No articles discovered. Exiting.")
        print("=====================================")
        print("=== News Bot - Run Finished ===")
        print("=====================================")
        return

    print(f"Discovered {len(discovered_articles)} potential articles.")
    for i, art in enumerate(discovered_articles):
        print(f"  {i+1}. Title: {art.get('title', 'N/A')} | URL: {art.get('url', 'N/A')}")

    final_news_reports = []
    processed_urls = set() # To avoid processing the same URL multiple times if Perplexity returns duplicates

    # Step 2 & 3: Process and Summarize each article
    print("\n--- Step 2 & 3: Processing and Summarizing Articles ---")
    for i, article_info in enumerate(discovered_articles):
        original_title = article_info.get("title", "N/A")
        article_url = article_info.get("url")

        print(f"\nProcessing article {i+1}/{len(discovered_articles)}: '{original_title}' ({article_url})")

        if not article_url or not article_url.startswith("http"):
            print(f"Skipping article with invalid or missing URL: {article_url}")
            continue
        
        if article_url in processed_urls:
            print(f"Skipping already processed URL: {article_url}")
            continue
        processed_urls.add(article_url)

        # 2a. Fetch and extract text
        article_text = article_handler.fetch_and_extract_text(article_url)
        if not article_text:
            print(f"Failed to fetch or extract text for {article_url}. Skipping.")
            continue

        # 2b. Verify article
        verification_results = article_handler.verify_article_with_gemini(article_text, article_url)
        if not verification_results:
            print(f"Failed to get verification results for {article_url}. Skipping.")
            continue
        
        print(f"  Verification for {article_url}: Date='{verification_results.get('publication_date_str')}', Recent='{verification_results.get('is_recent')}', Relevant='{verification_results.get('is_relevant')}', Type='{verification_results.get('article_type_assessment')}'")

        # Check verification status before summarization
        is_suitable_for_summary = (
            verification_results.get("is_recent") == "Recent" and
            verification_results.get("is_relevant") == "Relevant" and
            verification_results.get("article_type_assessment") == "News article"
        )

        if not is_suitable_for_summary:
            print(f"Article {article_url} not suitable for summary based on verification (Recent: {verification_results.get('is_recent')}, Relevant: {verification_results.get('is_relevant')}, Type: {verification_results.get('article_type_assessment')}). Skipping summarization.")
            continue
        
        print(f"Article {article_url} verified as suitable. Proceeding to summarization.")

        # 3. Generate summary
        news_summary = summarizer.generate_summary_with_gemini(article_text, article_url, original_title)
        if not news_summary or "failed" in news_summary.lower() or "skipped" in news_summary.lower():
            print(f"Failed to generate summary for {article_url} or summary was invalid. Skipping.")
            continue
            
        print(f"  Successfully generated summary for {article_url}.")

        final_news_reports.append({
            "news_id": len(final_news_reports) + 1,
            "original_title": original_title,
            "source_url": article_url,
            "reported_publication_date": verification_results.get("publication_date_str", "N/A"),
            "verification_details": verification_results, # Includes relevance, factuality, etc.
            "summary": news_summary,
            "processing_timestamp": datetime.now().isoformat()
        })
        
        if len(final_news_reports) >= config.MAX_SEARCH_RESULTS_TO_PROCESS: # Should ideally be a different limit for *final reports*
            print(f"Reached maximum number of desired news reports ({len(final_news_reports)}). Stopping further processing.")
            break

    # Step 4: Save the compiled news reports
    print("\n--- Step 4: Saving News Reports ---")
    if final_news_reports:
        output_filename_base = "weekly_news_report"
        saved_filepath = file_manager.save_data_to_json(final_news_reports, output_filename_base)
        if saved_filepath:
            print(f"Successfully saved {len(final_news_reports)} news reports to {saved_filepath}")
        else:
            print("Failed to save the news reports.")
    else:
        print("No news reports were generated to save.")

    print("=====================================")
    print(f"=== News Bot - Run Finished at {datetime.now().isoformat()} ===")
    print("=====================================")

if __name__ == '__main__':
    # This allows running the bot directly using: python -m news_bot.main_orchestrator
    run_news_bot() 