# news_bot/generation/summarizer.py

from ..core import config
from ..utils import prompt_logger, openrouter_client

def generate_summary_with_gemini(school: dict[str, str], article_text: str, article_url: str, article_title: str = "") -> str | None:
    """
    Generates a professional English news summary using Gemini 2.5 Pro.
    Emphasizes accuracy and factuality - only includes information present in the article.
    """
    if not config.OPENROUTER_API_KEY:
        print("Error: OPENROUTER_API_KEY not configured for summarization.")
        return None
    if not article_text or not article_text.strip():
        print(f"Info: Skipping summarization for {article_url} due to empty article text.")
        return "Summarization skipped: Article text was empty."

    print(f"Generating English summary with OpenRouter ({config.GEMINI_PRO_MODEL}) for: {article_url[:100]}...")

    title_context = f"The original article title is: '{article_title}'. " if article_title and article_title != "N/A" else ""

    # Use Pro model's larger context limit
    context_char_limit = getattr(config, 'GEMINI_PRO_MODEL_CONTEXT_LIMIT_CHARS', 2000000)
    article_text_limit = min(len(article_text), context_char_limit // 2)  # Use half for safety

    # Get school-specific context from the school profile
    school_name = school.get('school_name', 'the university')
    school_location = school.get('school_location', 'the local area')
    audience_en = school.get('prompt_context', {}).get('audience_en', f'Chinese international students at {school_name}')
    
    prompt = f"""You are a professional English-language news writer. Your task is to create a detailed yet concise news summary based on the provided article text.

## Role
You are a professional English-language news writer specializing in accurate, factual reporting.

## Task
Create a detailed yet concise news summary (approximately 5-7 sentences, or 100-180 words) based on the provided article text.
The summary is for {audience_en}.

## Requirements

### Accuracy & Factuality (Highest Priority)
- Include ONLY information explicitly stated in the article text
- Do NOT infer, guess, or add information not present in the article
- Do NOT include personal opinions, interpretations, or conclusions not in the original text
- Verify all dates, names, and numbers against the article text
- If information is unclear or missing, do not fill in gaps with assumptions

### Content Requirements
Focus on key information most relevant to {audience_en}, especially concerning:
- Their studies, work, daily life, or immigration/visa policies
- Events or policies in {school_location} or the U.S.

Key points to cover, ensuring important details are retained:
- What happened (core event/announcement)?
- When and where did it happen (specific dates, locations)?
- Who was involved (key individuals, groups, departments)?
- Main consequences, implications, or direct impacts for {audience_en}
- Include crucial numbers, statistics, or significant outcomes

### Style Requirements
- Maintain a factual and objective tone
- Use clear, professional language
- Provide the summary directly, without introductory phrases like 'This article is about...'
- Write in complete sentences with proper grammar

### Format Requirements
- Length: 5-7 sentences, or 100-180 words
- Structure: Coherent narrative flow, not bullet points

## Input Data

{title_context}The article URL is: {article_url} (for your reference).

--- Full Article Text (first {article_text_limit} characters) ---
{article_text[:article_text_limit]}
--- End of Article Text ---

## Output

Detailed News Summary (5-7 sentences, 100-180 words, for {audience_en}):
""" 

    try:
        print(f"Sending summarization request to OpenRouter API ({config.GEMINI_PRO_MODEL})...")
        
        # Log the prompt
        prompt_logger.log_prompt(
            "generate_summary_with_gemini",
            prompt,
            context={
                "article_url": article_url,
                "article_title": article_title,
                "school": school.get('school_name', 'Unknown'),
                "article_text_length": len(article_text)
            }
        )
        
        summary_text = openrouter_client.generate_content(
            prompt=prompt,
            model=config.GEMINI_PRO_MODEL,
            temperature=0.7
        )

        if not summary_text:
            print(f"Warning: Empty summary received from OpenRouter for {article_url}. Text length: {len(article_text)} chars.")
            return "Summarization failed: AI returned empty response."

        print(f"Successfully generated English summary for {article_url[:100]}...")
        return summary_text

    except Exception as e:
        print(f"Error during OpenRouter API call for summarization of {article_url}: {e}")
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