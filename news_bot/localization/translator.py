# news_bot/localization/translator.py

import google.generativeai as genai
from ..core import config
import re

def translate_and_restyle_to_chinese(english_summary_data: dict) -> dict | None:
    """
    Translates an English news summary to Chinese, rewrites it in a serious news style,
    includes date/source, formats names, and generates a Chinese title.

    Args:
        english_summary_data: Dict with 'summary', 'source_url', 
                               'reported_publication_date', 'original_title'.

    Returns:
        A dictionary with keys 'chinese_news_report' and 'chinese_title',
        or None if an error occurs.
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
        "chinese_news_report": "翻译失败或跳过 (Translation failed or skipped)"
    }

    if not english_summary.strip():
        print("Skipping translation for empty English summary.")
        return {
            "chinese_title": "无标题 (No title)",
            "chinese_news_report": "翻译跳过：英文摘要为空 (Translation skipped: English summary was empty)"
        }

    print(f"Translating, restyling, and generating title for: {source_url}")
    try:
        genai.configure(api_key=config.GEMINI_API_KEY)
        model = genai.GenerativeModel(config.GEMINI_FLASH_MODEL) 
    except Exception as e:
        print(f"Error initializing Gemini model for translation: {str(e)}")
        return None # Or return default_error_return

    prompt = f"""Please perform the following tasks on the provided English news summary:
1.  Create a concise, relevant, and catchy news title in Simplified Chinese (简体中文) for the news. The title should summarize the main point of the news. Place this title on the VERY FIRST line of your response, prefixed with "Chinese Title:".
2.  On subsequent lines, provide the full news report: Translate the English summary into Simplified Chinese (简体中文).
3.  Rewrite the translated summary in a serious, formal, and objective news reporting style suitable for university students. Use a serious tone and formal language; be a professional news reporter.
4.  Incorporate the publication date and source information naturally within the Chinese news report body. Use the phrase "据WSN报道
5.  VERY IMPORTANT: For all not very popular English names of people, organizations, or programs mentioned in the text, translate them into Chinese and then immediately follow with the original English name in parentheses. Example: 琳达·G·米尔斯 (Linda G. Mills). For NYU, Trump, or other popular names, just use the Chinese name.
6.  The final output after "Chinese Title:" should be ONLY the complete Chinese news report body. Do not include any of your own commentary, introductions, or the original English text in the report body.

Example of your full response (title on first line, report on following lines):
Chinese Title: [Your Generated Chinese Title Here]
[Full Chinese news report body starts here, incorporating date, source, and formatted names...]

Original English Summary:
'''
{english_summary}
'''

Publication Date: {publication_date}
Source URL (for deriving source name): {source_url}
Original Article Title (for context): {original_title}
(If source is nyunews.com, use "WSN" as the source name in Chinese attribution, e.g., "据WSN报道")

Your response (Chinese title on first line, then the Chinese news report body):
"""

    try:
        print(f"Sending translation/title request to Gemini API ({config.GEMINI_FLASH_MODEL})...")
        response = model.generate_content(prompt)
        
        full_response_text = ""
        if hasattr(response, 'text'):
            full_response_text = response.text.strip()
        elif hasattr(response, 'parts') and response.parts:
            for part in response.parts:
                if hasattr(part, 'text'):
                    full_response_text += part.text.strip()
            full_response_text = full_response_text.strip()
        else:
            print(f"Error: Gemini translation/title response for {source_url} in unexpected format.")
            return default_error_return
        
        if not full_response_text:
            print(f"Warning: Empty response received from Gemini for {source_url}.")
            return default_error_return

        lines = full_response_text.split('\n', 1) # Split only on the first newline
        chinese_title = "标题提取失败 (Title extraction failed)"
        chinese_news_report = "正文提取失败 (Report body extraction failed)"

        if lines[0].startswith("Chinese Title:"):
            chinese_title = lines[0].replace("Chinese Title:", "").strip()
            if len(lines) > 1:
                chinese_news_report = lines[1].strip()
            else:
                 print(f"Warning: Gemini response had title but no report body for {source_url}.")
        else:
            print(f"Warning: Gemini response did not start with 'Chinese Title:' for {source_url}. Entire response treated as report body.")
            chinese_news_report = full_response_text # Assume entire response is the body if title format is wrong

        print(f"Successfully processed translation/title for {source_url}.")
        return {"chinese_title": chinese_title, "chinese_news_report": chinese_news_report}

    except Exception as e:
        print(f"Error during Gemini API call for translation/title of {source_url}: {e}")
        return default_error_return

if __name__ == '__main__':
    print("Testing Translator Module...")
    import sys
    import os
    if '..'.join(os.path.abspath(__file__).split(os.sep)[:-2]) not in sys.path:
         sys.path.insert(0, '..'.join(os.path.abspath(__file__).split(os.sep)[:-2]))
    
    from news_bot.core import config 
    config.validate_config() 

    sample_english_data = {
        "summary": "NYU announced a new visa support initiative for international students, including workshops and extended advising. This responds to reported delays, especially for students from China. University President Linda G. Mills affirmed NYU's commitment to its global community. The changes aim to benefit hundreds for the upcoming academic year.",
        "source_url": "https://www.nyu.edu/news/2024/05/21/visa-support-initiative.html",
        "reported_publication_date": "2024-05-21",
        "original_title": "NYU Launches New Visa Support Initiative for International Students"
    }

    print(f"\n--- Test Translation & Title for: {sample_english_data['source_url']} ---")
    translation_output = translate_and_restyle_to_chinese(sample_english_data)

    if translation_output:
        print(f"\nGenerated Chinese Title: {translation_output.get('chinese_title')}")
        print(f"\nGenerated Chinese News Report:\n{translation_output.get('chinese_news_report')}")
    else:
        print("\nFailed to generate Chinese news report and title.") 