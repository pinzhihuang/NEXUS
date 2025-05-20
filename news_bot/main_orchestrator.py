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
    Main function to run the news bot workflow:
    1. Discover articles.
    2. For each article: fetch, verify.
    3. If verified, generate detailed English summary.
    4. Translate to Chinese (title, report) and then refine Chinese report.
    5. Save compiled reports.
    """
    run_start_time = datetime.now()
    print("===========================================")
    print("=== LIVE Weekly News Bot - Starting Run ===")
    print(f"=== Run timestamp: {run_start_time.isoformat()} ===")
    print("===========================================")

    try:
        config.validate_config()
    except ValueError as e_config:
        print(f"CRITICAL Configuration Error: {e_config}")
        print("Bot run aborted.")
        return

    print("\n--- Step 1: Discovering Articles ---")
    discovered_articles = search_client.find_relevant_articles()

    if not discovered_articles:
        print("Info: No articles discovered from any source. Exiting.")
        print("=====================================")
        print(f"=== News Bot - Run Finished at {datetime.now().isoformat()} ===")
        print("=====================================")
        return

    print(f"Info: Discovered {len(discovered_articles)} potential articles overall.")

    final_news_reports = []
    processed_urls = set()
    articles_processed_count = 0

    print("\n--- Steps 2-4: Processing, Summarizing, Translating, and Refining Articles ---")
    for i, article_info in enumerate(discovered_articles):
        if len(final_news_reports) >= config.MAX_FINAL_REPORTS:
            print(f"Info: Reached maximum number of final reports ({config.MAX_FINAL_REPORTS}). Stopping further processing.")
            break

        articles_processed_count += 1
        original_title = article_info.get("title", "N/A")
        article_url = article_info.get("url")
        source_method = article_info.get("source_method", "Unknown")

        print(f"\nProcessing article {articles_processed_count}/{len(discovered_articles)} (Source: {source_method}): '{original_title[:70]}...' ({article_url[:100]}...)")

        if not article_url or not article_url.startswith("http"):
            print(f"  Skipping: Invalid or missing URL ({article_url}).")
            continue
        
        if article_url in processed_urls:
            print(f"  Skipping: Already processed URL ({article_url[:100]}...).")
            continue
        processed_urls.add(article_url)

        # Step 2a: Fetch and extract text
        article_text = article_handler.fetch_and_extract_text(article_url)
        if not article_text:
            print(f"  Skipping: Failed to fetch or extract text.")
            continue

        # Step 2b: Verify article
        verification_results = article_handler.verify_article_with_gemini(article_text, article_url)
        if not verification_results:
            print(f"  Skipping: Failed to get verification results.")
            continue
        
        print(f"  Verification: Date='{verification_results.get('publication_date_str')}', Recent='{verification_results.get('is_recent')}', Rel='{verification_results.get('is_relevant')}', Type='{verification_results.get('article_type_assessment')}'")

        is_suitable_for_summary = (
            verification_results.get("is_recent", "").startswith("Recent") and
            verification_results.get("is_relevant") == "Relevant" and
            verification_results.get("article_type_assessment") == "News article"
        )

        if not is_suitable_for_summary:
            print(f"  Skipping: Article not suitable for summary (Recent: {verification_results.get('is_recent')}, Rel: {verification_results.get('is_relevant')}, Type: {verification_results.get('article_type_assessment')}).")
            continue
        
        print(f"  Info: Article verified. Proceeding to English summarization.")

        # Step 3: Generate English summary
        english_summary = summarizer.generate_summary_with_gemini(article_text, article_url, original_title)
        if not english_summary or "failed" in english_summary.lower() or "skipped" in english_summary.lower():
            print(f"  Skipping: Failed to generate English summary or summary invalid.")
            continue
        print(f"  Info: Successfully generated English summary.")

        # Step 4: Translate and Restyle to Chinese
        english_report_data_for_translation = {
            "summary": english_summary,
            "source_url": article_url,
            "reported_publication_date": verification_results.get("publication_date_str", "N/A"),
            "original_title": original_title
        }
        translation_output = translator.translate_and_restyle_to_chinese(english_report_data_for_translation)
        
        chinese_title = "中文标题失败"
        initial_chinese_report = "初步中文报道失败"
        refined_chinese_report = "优化中文报道失败"

        if translation_output:
            chinese_title = translation_output.get("chinese_title", chinese_title)
            initial_chinese_report = translation_output.get("chinese_news_report", initial_chinese_report)
            refined_chinese_report = translation_output.get("refined_chinese_news_report", initial_chinese_report)
            
            log_msg = "  Info: Chinese translation processed."
            if "失败" in chinese_title or "failed" in chinese_title.lower(): log_msg += " Title gen issue."
            if "失败" in refined_chinese_report or "failed" in refined_chinese_report.lower(): log_msg += " Refinement issue."
            print(log_msg)
        else:
            print(f"  Warning: Failed to get response from Chinese translation module.")

        final_news_reports.append({
            "news_id": len(final_news_reports) + 1,
            "original_title": original_title,
            "source_url": article_url,
            "source_method": source_method,
            "reported_publication_date": verification_results.get("publication_date_str", "N/A"),
            "verification_details": verification_results, 
            "english_summary": english_summary,
            "chinese_title": chinese_title, 
            "initial_chinese_report": initial_chinese_report,
            "refined_chinese_news_report": refined_chinese_report,
            "processing_timestamp": datetime.now().isoformat()
        })

    # Step 5: Save the compiled news reports
    print("\n--- Step 5: Saving News Reports ---")
    if final_news_reports:
        output_filename_base = "weekly_news_report"
        saved_filepath = file_manager.save_data_to_json(final_news_reports, output_filename_base)
        if saved_filepath:
            print(f"Successfully saved {len(final_news_reports)} news reports to {saved_filepath}")
        else:
            print("Error: Failed to save the news reports.")
    else:
        print("Info: No news reports were generated to save.")

    run_end_time = datetime.now()
    print("=====================================")
    print(f"=== News Bot - Run Finished at {run_end_time.isoformat()} ===")
    print(f"=== Total Run Duration: {run_end_time - run_start_time} ===")
    print("=====================================")

if __name__ == '__main__':
    run_news_bot() 