from .audit_client import GmailApi
import google.generativeai as genai

from ..core import config

def sanitize_email_using_gemini(email_body: str):    
    print(f"Sanitizing email using Gemini...")
    if not config.GEMINI_API_KEY:
        print("Error: GEMINI_API_KEY not configured for verification.")
        return None
    try:
        genai.configure(api_key=config.GEMINI_API_KEY)
        model = genai.GenerativeModel(config.GEMINI_FLASH_MODEL)
    except Exception as e:
        print(f"Error initializing Gemini model for verification: {str(e)}")
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
        response = model.generate_content(prompt)
        sanitized_email_body = getattr(response, 'text', '').strip()
        return sanitized_email_body
    except Exception as e:
        print(f"Error during Gemini API call for sanitization of email: {e}")
        return None
        