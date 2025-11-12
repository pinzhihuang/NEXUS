from .audit_client import GmailApi
from ..core import config
from ..utils import openrouter_client

def sanitize_email_using_gemini(email_body: str):    
    print(f"Sanitizing email using OpenRouter...")
    if not config.OPENROUTER_API_KEY:
        print("Error: OPENROUTER_API_KEY not configured for verification.")
        return None
    
    prompt = f"""Please sanitize the following email body. Your task is to:
1.  **Keep:** Subject and main content relevant to the subject.
2.  **Remove:** Footer information (social media links, contact details, legal disclaimers, unsubscribe links, etc.).
3.  **Remove:** Any image placeholders or descriptions.
4.  **Remove:** Any information before the subject e.g. "Dear [Name],", "To [Name],", "From [Name],", "Re: [Subject]", "Date: [Date]", etc.

Original Email Body:
{email_body}
"""

    try:
        sanitized_email_body = openrouter_client.generate_content(
            prompt=prompt,
            model=config.GEMINI_FLASH_MODEL,
            temperature=0.3
        )
        return sanitized_email_body
    except Exception as e:
        print(f"Error during OpenRouter API call for sanitization of email: {e}")
        return None
        