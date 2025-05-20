# news_bot/main_orchestrator.py

from datetime import datetime

from .core import config
from .discovery import search_client
from .processing import article_handler
from .generation import summarizer
from .utils import file_manager
from .localization import translator

def run_news_bot():
    """
    Main function to run the complete news bot workflow:
    1. Discover articles.
    2. For each article:
        a. Fetch and extract text.
        b. Verify for recency, relevance, and if it IS a news article.
        c. If verified, generate a detailed English summary.
        d. Translate and restyle to Chinese, including a Chinese title.
    3. Save the compiled news reports (English and Chinese versions, Chinese title).
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

    # Step 2, 3 & Translation: Process, Summarize, and Translate each article
    print("\n--- Step 2, 3 & Translation: Processing, Summarizing, and Translating Articles ---")
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
        
        print(f"  Verification: Date='{verification_results.get('publication_date_str')}', Recent='{verification_results.get('is_recent')}', Relevant='{verification_results.get('is_relevant')}', Type='{verification_results.get('article_type_assessment')}'")

        # Check verification status before summarization
        is_suitable_for_summary = (
            verification_results.get("is_recent") == "Recent" and
            verification_results.get("is_relevant") == "Relevant" and
            verification_results.get("article_type_assessment") == "News article"
        )

        if not is_suitable_for_summary:
            print(f"Article not suitable for summary based on verification. Skipping.")
            continue
        
        print(f"Article verified. Proceeding to English summarization.")

        # 3. Generate English summary
        english_summary = summarizer.generate_summary_with_gemini(article_text, article_url, original_title)
        if not english_summary or "failed" in english_summary.lower() or "skipped" in english_summary.lower():
            print(f"Failed to generate English summary. Skipping.")
            continue
            
        print(f"  Successfully generated English summary.")

        # --- New Step: Translate and Restyle to Chinese ---
        english_report_data_for_translation = {
            "summary": english_summary,
            "source_url": article_url,
            "reported_publication_date": verification_results.get("publication_date_str", "N/A"),
            "original_title": original_title
        }
        translation_output = translator.translate_and_restyle_to_chinese(english_report_data_for_translation)
        
        chinese_title = "中文标题生成失败 (Chinese title generation failed)"
        chinese_news_report = "中文报道翻译失败或跳过 (Chinese report translation failed or skipped)"

        if translation_output:
            chinese_title = translation_output.get("chinese_title", chinese_title)
            chinese_news_report = translation_output.get("chinese_news_report", chinese_news_report)
            if "失败" not in chinese_title and "failed" not in chinese_title.lower(): # Basic check if title was successful
                 print(f"  Successfully generated Chinese title and report for {article_url}.")
            else:
                 print(f"  Generated Chinese report for {article_url}, but title generation might have issues.")
        else:
            print(f"  Failed to get any response from Chinese translation module for {article_url}.")

        final_news_reports.append({
            "news_id": len(final_news_reports) + 1,
            "original_title": original_title,
            "source_url": article_url,
            "reported_publication_date": verification_results.get("publication_date_str", "N/A"),
            "verification_details": verification_results, # Includes relevance, factuality, etc.
            "english_summary": english_summary, # Added specific key for English summary
            "chinese_title": chinese_title, # Added Chinese title
            "chinese_news_report": chinese_news_report, # Added Chinese news report
            "processing_timestamp": datetime.now().isoformat()
        })
        
        if len(final_news_reports) >= config.MAX_FINAL_REPORTS: # Using MAX_FINAL_REPORTS
            print(f"Reached maximum number of final news reports ({len(final_news_reports)}). Stopping.")
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