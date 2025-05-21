# news_bot/localization/translator.py

import google.generativeai as genai
from ..core import config
# import re # Not strictly needed if not doing complex regex here

# Helper function for the refinement step
def _refine_chinese_news_report_with_gemini(chinese_text: str, source_url: str, publication_date: str, original_title: str) -> str:
    """
    Refines a Chinese news report using Gemini to improve conciseness, logic, and factuality.
    """
    if not chinese_text.strip() or "失败" in chinese_text or "failed" in chinese_text.lower() or "跳过" in chinese_text:
        print(f"Info: Skipping refinement for placeholder or error text: '{chinese_text[:50]}...'")
        return chinese_text 

    print(f"Refining Chinese news report for: {source_url[:100]}...")
    try:
        model = genai.GenerativeModel(config.GEMINI_FLASH_MODEL) # Or a specific model for refinement
    except Exception as e:
        print(f"Error initializing Gemini model for refinement: {str(e)}")
        return chinese_text # Return original on error

    prompt = f"""Please refine the following Chinese news report. Your task is to:
1.  Ensure the report is strongly logical, coherent, and strictly factual, maintaining a serious news tone.
2.  Remove any sentences or phrases that do not add factual value to the core news story.
3.  Aim for conciseness while preserving all critical information relevant to the English title ('{original_title}').
4.  The output should be ONLY the refined Chinese news report. Do not add any commentary.
5.  Pay more attention to the last sentence of the report. This sentence is sometimes off-topic.

Original Chinese News Report to Refine:
'''
{chinese_text}
'''

Refined Chinese News Report:
"""

    try:
        print(f"Sending refinement request to Gemini API ({config.GEMINI_FLASH_MODEL})...")
        response = model.generate_content(prompt)
        refined_text = getattr(response, 'text', '').strip()
        if not refined_text and hasattr(response, 'parts') and response.parts:
            for part in response.parts:
                refined_text += getattr(part, 'text', '').strip()
            refined_text = refined_text.strip()

        if not refined_text:
            print(f"Warning: Empty response from Gemini during refinement for {source_url}. Returning original.")
            return chinese_text
        
        print(f"Successfully refined Chinese news report for {source_url[:100]}...")
        return refined_text
    except Exception as e:
        print(f"Error during Gemini API call for refinement of {source_url}: {e}")
        return chinese_text # Return original on error

def translate_and_restyle_to_chinese(english_summary_data: dict) -> dict | None:
    """
    Translates English summary to Chinese, restyles, includes date/source,
    formats names, and generates a Chinese title.
    """
    if not config.GEMINI_API_KEY:
        print("Error: GEMINI_API_KEY not configured for translation.")
        return None

    english_summary = english_summary_data.get('summary', '')
    source_url = english_summary_data.get('source_url', 'Unknown source')
    publication_date = english_summary_data.get('reported_publication_date', 'Date not available')
    original_title = english_summary_data.get('original_title', 'N/A')

    default_error_return = {
        "chinese_title": "标题生成失败 (Title generation failed)",
        "chinese_news_report": "翻译失败或跳过 (Translation failed or skipped)",
        "refined_chinese_news_report": "中文报道未作优化 (Chinese report not refined due to prior error)"
    }

    if not english_summary.strip():
        print(f"Info: Skipping translation for {source_url} due to empty English summary.")
        return {
            "chinese_title": "无标题 (No title for empty summary)",
            "chinese_news_report": "翻译跳过：英文摘要为空 (Translation skipped: English summary was empty)",
            "refined_chinese_news_report": "中文报道未作优化 (Chinese report not refined as summary was empty)"
        }

    print(f"Initial translation, restyling, and Chinese title generation for: {source_url[:100]}...")
    try:
        genai.configure(api_key=config.GEMINI_API_KEY)
        model = genai.GenerativeModel(config.GEMINI_FLASH_MODEL) 
    except Exception as e:
        print(f"Error initializing Gemini model for translation: {str(e)}")
        return default_error_return

    source_name_for_prompt = "新闻来源"
    if "nyunews.com" in source_url: source_name_for_prompt = "WSN"
    elif "nyu.edu" in source_url: source_name_for_prompt = "NYU官网"
    
    context_char_limit = getattr(config, 'GEMINI_FLASH_MODEL_CONTEXT_LIMIT_CHARS', 100000)

    prompt = f"""Please perform the following tasks on the provided English news summary:
1.  Create a concise, relevant, and catchy news title in Simplified Chinese (简体中文). Place this title on the VERY FIRST line, prefixed with "Chinese Title:".
2.  On subsequent lines, provide the full news report: Read the English summary and rewrite it into Simplified Chinese news article.
3.  Rewrite the translation in a serious, formal, and objective news reporting style. 
4.  Use short sentences and actuate words. Keep the news report coherent, professional, and logical. Do not include any additional commentary or opinion. Do not write any conclusions. If mentioned, you can end the article with the newest updates regarding the topic. For example, "目前，学校对此事件还没有做出回应。"
5.  [Important] Keep the language natural and professional. Try not to use adjectives.
5.  [IMPORTANT] Do not include any consequence, implication, or opinions of this news topics. We need only facts. Avoid using words like "可能","引发", etc.
6.  [IMPORTANT] Keep the logic between sentences coherent and organized. Do not try to include all the information from the original English summary.
7.  If the english summary contains multiple news topics, select the most important one and focus on it. Keep the article coherent.
8.  For less common English names of people, organizations, or programs, translate to Chinese and follow with the original English in parentheses: 中文名 (English Name). For very well-known entities like NYU or common English names, direct Chinese translation is fine.
9.  The final output after "Chinese Title:" should be ONLY the Chinese news report body.

Original English Summary (for translation):
'''
{english_summary}
'''
Original Article Title (for context): {original_title}

Your response (Chinese title on first line, then the Chinese news report body):
"""
    initial_chinese_title = default_error_return["chinese_title"]
    initial_chinese_report = default_error_return["chinese_news_report"]

    try:
        print(f"Sending translation/title request to Gemini API ({config.GEMINI_FLASH_MODEL})...")
        response = model.generate_content(prompt)
        
        full_response_text = getattr(response, 'text', '').strip()
        if not full_response_text and hasattr(response, 'parts') and response.parts:
            for part in response.parts:
                full_response_text += getattr(part, 'text', '').strip()
            full_response_text = full_response_text.strip()
        
        if full_response_text:
            lines = full_response_text.split('\n', 1)
            if lines[0].startswith("Chinese Title:"):
                initial_chinese_title = lines[0].replace("Chinese Title:", "").strip()
                if len(lines) > 1:
                    initial_chinese_report = lines[1].strip()
                else:
                    print(f"Warning: Gemini response had title but no report body for {source_url}. Using title as body for now.")
                    initial_chinese_report = initial_chinese_title # Might be an error, or title only was returned
            else:
                print(f"Warning: Gemini response did not start with 'Chinese Title:' for {source_url}. Entire response treated as report body.")
                initial_chinese_report = full_response_text
        else:
            print(f"Warning: Empty response from Gemini for initial translation/title of {source_url}.")
            # Errors already set in initial_chinese_title/report

    except Exception as e:
        print(f"Error during Gemini API call for initial translation/title of {source_url}: {e}")
        # Errors already set in initial_chinese_title/report

    # Ensure some content exists for both, even if it's an error placeholder from parsing
    if not initial_chinese_title.strip(): initial_chinese_title = default_error_return["chinese_title"]
    if not initial_chinese_report.strip(): initial_chinese_report = default_error_return["chinese_news_report"]

    print(f"Initial Chinese processing for {source_url[:100]}... complete. Title: '{initial_chinese_title}'")

    # --- Refinement Step ---
    refined_report = _refine_chinese_news_report_with_gemini(initial_chinese_report, source_url, publication_date, original_title)
    # --- End Refinement Step ---

    return {
        "chinese_title": initial_chinese_title,
        "chinese_news_report": initial_chinese_report, # Keep the initial one for comparison/auditing if needed
        "refined_chinese_news_report": refined_report
    }

if __name__ == '__main__':
    print("Testing Translator Module (with Refinement)...")
    import sys
    import os
    PROJECT_ROOT_FOR_TEST = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if PROJECT_ROOT_FOR_TEST not in sys.path:
         sys.path.insert(0, PROJECT_ROOT_FOR_TEST)
    
    from news_bot.core import config 
    config.validate_config()
    if not hasattr(config, 'GEMINI_FLASH_MODEL_CONTEXT_LIMIT_CHARS'):
        config.GEMINI_FLASH_MODEL_CONTEXT_LIMIT_CHARS = 100000

    sample_english_data = {
        "summary": "NYU announced a new visa support initiative. This helps international students, especially those from China, facing visa delays. President Linda G. Mills stated NYU is committed. Workshops and extended advising are included. Hundreds will benefit next academic year.",
        "source_url": "https://www.nyu.edu/news/2024/05/21/visa-support-initiative.html",
        "reported_publication_date": "2024-05-21",
        "original_title": "NYU Launches New Visa Support Initiative for International Students"
    }

    print(f"\n--- Test Translation, Title & Refinement for: {sample_english_data['source_url']} ---")
    translation_output = translate_and_restyle_to_chinese(sample_english_data)

    if translation_output:
        print(f"\nGenerated Chinese Title: {translation_output.get('chinese_title')}")
        print(f"\nInitial Chinese News Report:\n{translation_output.get('chinese_news_report')}")
        print(f"\nRefined Chinese News Report:\n{translation_output.get('refined_chinese_news_report')}")
    else:
        print("\nFailed to generate Chinese news report and title (None returned).") 