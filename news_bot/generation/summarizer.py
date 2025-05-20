# news_bot/generation/summarizer.py

import google.generativeai as genai
from ..core import config

def generate_summary_with_gemini(article_text: str, article_url: str, article_title: str = "") -> str | None:
    """
    Generates a professional news summary using the Gemini API.

    Args:
        article_text: The full text content of the verified article.
        article_url: The URL of the article (for context and potential inclusion in summary if desired).
        article_title: The original title of the article (optional, for context).

    Returns:
        A string containing the generated news summary, or None if an error occurs.
    """
    if not config.GEMINI_API_KEY:
        print("Error: GEMINI_API_KEY not configured for summarization.")
        return None
    if not article_text or not article_text.strip():
        print(f"Skipping summarization for {article_url} due to empty article text.")
        return "Summarization skipped: Article text was empty."

    print(f"Generating summary with Gemini for: {article_url}")
    try:
        genai.configure(api_key=config.GEMINI_API_KEY)
        # Using the model specified in config, e.g., GEMINI_SUMMARY_MODEL
        model = genai.GenerativeModel(config.GEMINI_SUMMARY_MODEL)
    except Exception as e:
        print(f"Error initializing Gemini model for summarization: {str(e)}")
        return None

    title_context = f"The original article title is: '{article_title}'. " if article_title else ""

    # Prompt designed for creating a professional news summary for a specific audience
    prompt = f"""You are a professional English-language news writer. Your task is to create a concise and neutral news summary (approximately 3-5 sentences, or 70-120 words) 
based on the provided article text. The summary is for Chinese international students at New York University (NYU). 
Focus on the key information most relevant to their studies, work, daily life, or immigration/visa policies, especially concerning events or policies in New York or the U.S.

Key points to cover in the summary if present in the article:
- What happened?
- When and where did it happen?
- Who was involved?
- What are the main consequences or implications, particularly for the target audience?

Maintain a factual and objective tone. Do not add personal opinions or information not present in the article text. 
Do not include an introductory phrase like 'This article is about...'. Just provide the summary directly.

{title_context}The article URL is: {article_url} (for your reference, do not necessarily include it in the summary unless it's a critical part of the news itself).

--- Full Article Text (first 100,000 characters) ---
{article_text[:100000]}
--- End of Article Text ---

Concise News Summary (3-5 sentences for Chinese international students at NYU):
""" 

    # print(f"Gemini Summarization Prompt (first 500 chars):\n{prompt[:500]}...") # For debugging

    try:
        print(f"Sending summarization request to Gemini API ({config.GEMINI_SUMMARY_MODEL})...")
        response = model.generate_content(prompt)
        
        summary_text = ""
        if hasattr(response, 'text'):
            summary_text = response.text.strip()
        elif hasattr(response, 'parts') and response.parts:
            for part in response.parts:
                if hasattr(part, 'text'):
                    summary_text += part.text.strip()
            summary_text = summary_text.strip()
        else:
            print(f"Error: Gemini summarization response for {article_url} in unexpected format.")
            return None
        
        if not summary_text:
            print(f"Warning: Empty summary received from Gemini for {article_url}. Original text length: {len(article_text)} chars.")
            return "Summarization failed: AI returned an empty response."

        print(f"Successfully generated summary for {article_url}.")
        return summary_text

    except Exception as e:
        print(f"Error during Gemini API call for summarization of {article_url}: {e}")
        # import traceback
        # traceback.print_exc()
        return None

if __name__ == '__main__':
    # This is for testing the module directly
    print("Testing Summarizer Module...")
    import sys
    import os
    # Path adjustments for direct execution
    if '..'.join(os.path.abspath(__file__).split(os.sep)[:-2]) not in sys.path:
         sys.path.insert(0, '..'.join(os.path.abspath(__file__).split(os.sep)[:-2]))
    
    from news_bot.core import config # Re-import
    config.validate_config() # Check API keys

    # Example article text (replace with actual fetched text for real testing)
    sample_article_text = ("""
    New York University (NYU) today announced a new initiative to support international students 
    facing challenges with the recent changes in U.S. visa application processes. The initiative, 
    detailed on the NYU Office of Global Services website, includes dedicated workshops, extended 
    advising hours, and a new online portal for document submission. This comes after several 
    students, particularly from China, reported increased scrutiny and delays. University President 
    Linda G. Mills stated, "NYU is committed to its global community, and we will provide all 
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

    # Test with empty text
    print(f"\n--- Test Summarization for empty text ---")
    summary_empty = generate_summary_with_gemini("", "http://example.com/empty")
    if summary_empty:
        print("\nGenerated Summary (for empty text):")
        print(summary_empty)
    else:
        print("\nFailed to generate summary for empty text (or handled as expected).") 