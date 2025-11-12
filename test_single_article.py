#!/usr/bin/env python3
"""
Test script to process a single article URL through the full pipeline.
Usage: python test_single_article.py <article_url>
"""

import sys
from datetime import datetime

from news_bot.core import config, school_config
from news_bot.processing import article_handler
from news_bot.generation import summarizer
from news_bot.localization import translator
from news_bot.utils import file_manager, prompt_logger

def test_single_article(article_url: str, school_id: int = 5):
    """
    Test the full pipeline with a single article URL.
    
    Args:
        article_url: The URL of the article to process
        school_id: School ID (5 = USC)
    """
    print("=" * 80)
    print("=== Testing Single Article Pipeline ===")
    print(f"=== Article URL: {article_url} ===")
    print("=" * 80)
    
    # Initialize prompt logging
    prompt_log_file = prompt_logger.initialize_prompt_log()
    print(f"=== Prompt logging enabled: {prompt_log_file} ===\n")
    
    # Get school profile
    schools_dict = school_config.SCHOOL_PROFILES
    school = list(schools_dict.values())[school_id - 1]
    print(f"School: {school['school_name']}\n")
    
    # Step 1: Fetch and extract text
    print("--- Step 1: Fetching and Extracting Article Text ---")
    article_text = article_handler.fetch_and_extract_text(article_url)
    if not article_text:
        print("ERROR: Failed to fetch or extract text from article.")
        return None
    
    print(f"Successfully extracted {len(article_text)} characters of text.\n")
    
    # Step 2: Verify article
    print("--- Step 2: Verifying Article ---")
    verification_results = article_handler.verify_article_with_gemini(
        school, article_text, article_url, None
    )
    
    if not verification_results:
        print("ERROR: Failed to get verification results.")
        return None
    
    print(f"Verification Results:")
    print(f"  Publication Date: {verification_results.get('publication_date_str')}")
    print(f"  Recent Status: {verification_results.get('is_recent')}")
    print(f"  Relevant: {verification_results.get('is_relevant')}")
    print(f"  Article Type: {verification_results.get('article_type_assessment')}\n")
    
    # Step 3: Generate English summary
    print("--- Step 3: Generating English Summary ---")
    original_title = article_url.split('/')[-1].replace('-', ' ').title()  # Extract title from URL
    english_summary = summarizer.generate_summary_with_gemini(
        school, article_text, article_url, original_title
    )
    
    if not english_summary or "failed" in english_summary.lower():
        print("ERROR: Failed to generate English summary.")
        return None
    
    print(f"English Summary ({len(english_summary)} characters):")
    print(f"{english_summary}\n")
    
    # Step 4: Translate to Chinese
    print("--- Step 4: Translating to Chinese ---")
    english_report_data_for_translation = {
        "summary": english_summary,
        "source_url": article_url,
        "reported_publication_date": verification_results.get("publication_date_str", "N/A"),
        "original_title": original_title
    }
    
    translation_output = translator.translate_and_restyle_to_chinese(english_report_data_for_translation)
    
    if not translation_output:
        print("ERROR: Failed to translate to Chinese.")
        return None
    
    chinese_title = translation_output.get("chinese_title", "翻译失败")
    refined_chinese_report = translation_output.get("refined_chinese_news_report", "翻译失败")
    
    print(f"Chinese Title: {chinese_title}\n")
    print(f"Chinese Report ({len(refined_chinese_report)} characters):")
    print(f"{refined_chinese_report}\n")
    
    # Step 5: Compile results
    final_report = {
        "news_id": 1,
        "original_title": original_title,
        "source_url": article_url,
        "source_method": "manual_test",
        "reported_publication_date": verification_results.get("publication_date_str", "N/A"),
        "verification_details": verification_results,
        "english_summary": english_summary,
        "chinese_title": chinese_title,
        "refined_chinese_news_report": refined_chinese_report,
        "processing_timestamp": datetime.now().isoformat()
    }
    
    # Step 6: Save to JSON
    print("--- Step 5: Saving Results ---")
    saved_filepath = file_manager.save_data_to_json([final_report], "test_single_article", timestamp_in_filename=True)
    if saved_filepath:
        print(f"Results saved to: {saved_filepath}\n")
    
    # Write footer to prompt log
    prompt_log_file = prompt_logger.get_prompt_log_file()
    if prompt_log_file:
        try:
            with open(prompt_log_file, 'a', encoding='utf-8') as f:
                f.write("\n" + "=" * 80 + "\n")
                f.write(f"Test completed: {datetime.now().isoformat()}\n")
                f.write(f"Article URL: {article_url}\n")
                f.write(f"Total Prompts Logged: {prompt_logger.get_prompt_count()}\n")
                f.write("=" * 80 + "\n")
            print(f"=== Prompt log saved: {prompt_log_file} ===")
        except Exception as e:
            print(f"Warning: Failed to write footer to prompt log: {e}")
    
    print("\n" + "=" * 80)
    print("=== Test Complete ===")
    print("=" * 80)
    
    return final_report

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python test_single_article.py <article_url> [school_id]")
        print("\nExample:")
        print("  python test_single_article.py 'https://www.uscannenbergmedia.com/2025/10/29/from-nyu-to-usc-dr-carol-kim-as-new-vice-president-for-enrollment-management/' 5")
        sys.exit(1)
    
    article_url = sys.argv[1]
    school_id = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    
    try:
        config.validate_config()
    except ValueError as e:
        print(f"Configuration Error: {e}")
        sys.exit(1)
    
    result = test_single_article(article_url, school_id)
    if result:
        print("\n✓ Successfully processed article!")
    else:
        print("\n✗ Failed to process article.")
        sys.exit(1)

