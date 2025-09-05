# news_bot/generation/summarizer.py

import google.generativeai as genai
from ..core import config, school_config

def generate_summary_with_gemini(school: dict[str, str], article_text: str, article_url: str, article_title: str = "") -> str | None:
    """
    Generates a professional English news summary using the Gemini API.
    """
    if not config.GEMINI_API_KEY:
        print("Error: GEMINI_API_KEY not configured for summarization.")
        return None
    if not article_text or not article_text.strip():
        print(f"Info: Skipping summarization for {article_url} due to empty article text.")
        return "Summarization skipped: Article text was empty."

    print(f"Generating English summary with Gemini for: {article_url[:100]}...")
    try:
        genai.configure(api_key=config.GEMINI_API_KEY)
        model = genai.GenerativeModel(config.GEMINI_SUMMARY_MODEL)
    except Exception as e:
        print(f"Error initializing Gemini model for summarization: {str(e)}")
        return None

    title_context = f"The original article title is: '{article_title}'. " if article_title and article_title != "N/A" else ""

    # Determine a practical context limit for summarization task, can be different from verification
    # Using the same flash context limit for now, but could be a separate config if GEMINI_SUMMARY_MODEL is different
    context_char_limit = getattr(config, 'GEMINI_SUMMARY_MODEL_CONTEXT_LIMIT_CHARS', 
                                 getattr(config, 'GEMINI_FLASH_MODEL_CONTEXT_LIMIT_CHARS', 100000)) # Fallback

    prompt = f"""You are a professional English-language news writer. Your task is to create a detailed yet concise news summary 
(approximately 5-7 sentences, or 100-180 words) based on the provided article text. 
The summary is for {school['prompt_context']['audience_en']}. 
Focus on the key information most relevant to their studies, work, daily life, or immigration/visa policies, 
especially concerning events or policies in {school['school_location']} or the U.S.

Key points to cover, ensuring important details are retained:
- What happened (core event/announcement)?
- When and where did it happen (specific dates, locations)?
- Who was involved (key individuals, groups, departments)?
- Main consequences, implications, or direct impacts for {school['prompt_context']['audience_en']}.
- Include crucial numbers, statistics, or significant outcomes.

Maintain a factual and objective tone. Do not add personal opinions or information not in the article text. 
Provide the summary directly, without introductory phrases like 'This article is about...'.

{title_context}The article URL is: {article_url} (for your reference).

--- Full Article Text (first {context_char_limit} characters) ---
{article_text[:context_char_limit]}
--- End of Article Text ---

Detailed News Summary (5-7 sentences, 100-180 words, for {school['prompt_context']['audience_en']}):
""" 

    try:
        print(f"Sending summarization request to Gemini API ({config.GEMINI_SUMMARY_MODEL})...")
        response = model.generate_content(prompt)
        
        summary_text = getattr(response, 'text', '').strip()
        if not summary_text and hasattr(response, 'parts') and response.parts:
            for part in response.parts:
                summary_text += getattr(part, 'text', '').strip()
            summary_text = summary_text.strip()

        if not summary_text:
            print(f"Warning: Empty summary received from Gemini for {article_url}. Text length: {len(article_text)} chars.")
            return "Summarization failed: AI returned empty response."

        print(f"Successfully generated English summary for {article_url[:100]}...")
        return summary_text

    except Exception as e:
        print(f"Error during Gemini API call for summarization of {article_url}: {e}")
        return None

if __name__ == '__main__':
    print("Testing Summarizer Module...")
    import sys
    import os
    PROJECT_ROOT_FOR_TEST = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if PROJECT_ROOT_FOR_TEST not in sys.path:
         sys.path.insert(0, PROJECT_ROOT_FOR_TEST)
    
    from news_bot.core import config
    config.validate_config()
    # Add placeholders for context limits if not in config for testing
    if not hasattr(config, 'GEMINI_FLASH_MODEL_CONTEXT_LIMIT_CHARS'):
        config.GEMINI_FLASH_MODEL_CONTEXT_LIMIT_CHARS = 100000 
    if not hasattr(config, 'GEMINI_SUMMARY_MODEL_CONTEXT_LIMIT_CHARS'):
        config.GEMINI_SUMMARY_MODEL_CONTEXT_LIMIT_CHARS = 100000
        
    # use nyu as default school
    school = school_config.SCHOOL_PROFILES['nyu']

    sample_article_text = (f"""
    {school['school_name']} today announced a new initiative to support international students 
    facing challenges with the recent changes in U.S. visa application processes. The initiative, 
    detailed on the {school['school_name']} Office of Global Services website, includes dedicated workshops, extended 
    advising hours, and a new online portal for document submission. This comes after several 
    students, particularly from China, reported increased scrutiny and delays. University President 
    Linda G. Mills stated, "{school['school_name']} is committed to its global community, and we will provide all 
    necessary resources to help our international students navigate these complexities." The changes 
    are expected to benefit hundreds of students preparing for the upcoming academic year. The announcement 
    was made on May 21, 2024, and details are also available on the main NYU news page.
    """)
    sample_article_url = "https://www.nyu.edu/news/2024/05/21/visa-support-initiative.html"
    sample_article_title = "NYU Launches New Visa Support Initiative for International Students"

    print(f"\n--- Test Summarization for: {sample_article_url} ---")
    summary = generate_summary_with_gemini(sample_article_text, sample_article_url, sample_article_title)

    if summary:
        print("\nGenerated Summary:")
        print(summary)
    else:
        print("\nFailed to generate summary.") 