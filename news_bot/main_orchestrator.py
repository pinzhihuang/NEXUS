# news_bot/main_orchestrator.py

from datetime import datetime, date, timedelta

from .core import config, school_config
from .discovery import search_client
from .processing import article_handler
from .generation import summarizer
from .utils import file_manager
from .localization import translator
from .reporting import google_docs_exporter

def run_news_bot():
    """
    Main function to run the news bot workflow:
    1. Discover articles.
    2. For each article: fetch, verify.
    3. If verified, generate detailed English summary.
    4. Translate to Chinese (title, report) and then refine Chinese report.
    5. Save compiled reports to JSON and attempt to export to Google Doc.
    """
    run_start_time = datetime.now()
    print("===========================================")
    print("=== Project NEXUS - Student News Bot - Starting Run ===")
    print(f"=== Run timestamp: {run_start_time.isoformat()} ===")
    print("===========================================")

    try:
        config.validate_config()
    except ValueError as e_config:
        print(f"CRITICAL Configuration Error: {e_config}")
        print("Bot run aborted.")
        return
    
    # Pick school to collect news from
    print(f"=== Please pick a school to collect news from: ===")
    schools_dict = school_config.SCHOOL_PROFILES
    for school, info in schools_dict.items():
        print(f"  {info['id']}: {info['school_name']}")
    choosen_school_id = int(input("Please enter the ID of the school you want to collect news from: "))
    choosen_school = list(schools_dict.values())[choosen_school_id - 1]   

    # Get and display the configured date range
    start_date, end_date = config.get_news_date_range()
    print(f"\n=== Collecting news from: {start_date} to {end_date} ===")
    if config.NEWS_START_DATE:
        print(f"=== Using custom start date from configuration ===")
    else:
        print(f"=== Using automatic date range (last {config.RECENCY_THRESHOLD_DAYS} days) ===")

    print("\n--- Step 1: Discovering Articles ---")
    discovered_articles = search_client.find_relevant_articles(choosen_school)

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
        verification_results = article_handler.verify_article_with_gemini(choosen_school, article_text, article_url)
        if not verification_results:
            print(f"  Skipping: Failed to get verification results.")
            continue
        
        print(f"  Verification: Date='{verification_results.get('publication_date_str')}', Status='{verification_results.get('is_recent')}', Rel='{verification_results.get('is_relevant')}', Type='{verification_results.get('article_type_assessment')}'")

        # Use the explicit is_within_range flag if available, otherwise check for "Within range" in status
        is_within_date_range = verification_results.get("is_within_range", False)
        if not is_within_date_range:
            # Fallback for compatibility
            is_within_date_range = "Within range" in verification_results.get("is_recent", "") or "Recent" in verification_results.get("is_recent", "")
        
        is_suitable_for_summary = (
            is_within_date_range and
            verification_results.get("is_relevant") == "Relevant" and
            verification_results.get("article_type_assessment") == "News article"
        )

        if not is_suitable_for_summary:
            print(f"  Skipping: Article not suitable for summary (Within Range: {is_within_date_range}, Rel: {verification_results.get('is_relevant')}, Type: {verification_results.get('article_type_assessment')}).")
            continue
        
        print(f"  Info: Article verified. Proceeding to English summarization.")

        # Step 3: Generate English summary
        english_summary = summarizer.generate_summary_with_gemini(choosen_school, article_text, article_url, original_title)
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
        # Include date range in filename for clarity
        output_filename_base = f"weekly_student_news_report_{start_date}_{end_date}"
        saved_filepath = file_manager.save_data_to_json(final_news_reports, output_filename_base)
        if saved_filepath:
            print(f"Successfully saved {len(final_news_reports)} news reports to {saved_filepath}")
        else:
            print("Error: Failed to save the news reports.")
    else:
        print("Info: No news reports were generated to save.")

    # --- Step 6: Export to Google Doc ---
    if final_news_reports and saved_filepath:
        print("\n--- Step 6: Exporting News Reports to Google Doc ---")
        
        gdoc_title = f"Project NEXUS: Weekly Chinese News ({start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')})"
        
        gdoc_url = google_docs_exporter.update_or_create_news_document(choosen_school, final_news_reports, start_date, end_date)
        if gdoc_url:
            print(f"Successfully operated on Google Doc: {gdoc_url}")
        else:
            print("Error: Failed to operate on Google Doc.")
            print("Ensure Google Docs API is enabled, OAuth credentials correct, and app authorized.")
    elif not final_news_reports:
        print("Info: No reports to export to Google Doc.")

    run_end_time = datetime.now()
    print("=====================================")
    print(f"=== Project NEXUS - Run Finished at {run_end_time.isoformat()} ===")
    print(f"=== Total Run Duration: {run_end_time - run_start_time} ===")
    print(f"=== Date Range Processed: {start_date} to {end_date} ===")
    print("=====================================")

if __name__ == '__main__':
    run_news_bot()