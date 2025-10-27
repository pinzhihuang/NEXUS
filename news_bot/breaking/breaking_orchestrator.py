from .audit_client import GmailApi
from .email_sanitizer import sanitize_email_using_gemini

from ..core import config, school_config
from ..utils import file_manager
from ..localization import translator
from ..reporting import google_docs_exporter

from datetime import datetime

def orchestrate_breaking_news():
    client = GmailApi()
    emails = client.find_emails()
    email_reports = []
    
    for email in emails:
        sanitized_email_body = sanitize_email_using_gemini(email["decoded_message"])
        print(f"Sanitized email body: {sanitized_email_body}")
        
        english_report_data_for_translation = {
            "summary": sanitized_email_body,
            "source_url": email["subject"],
            "reported_publication_date": email["date"],
            "original_title": email["subject"]
        }
        translation_output = translator.translate_and_restyle_to_chinese(english_report_data_for_translation)
        email_reports.append(translation_output)
    
    # Save the compiled news reports    
    if email_reports:
        # Include date in filename for clarity
        breaking_news_date = email["date"]
        breaking_news_date = datetime.strptime(breaking_news_date, "%Y-%m-%d")
        output_filename_base = f"breaking_news_report_{breaking_news_date}"
        saved_filepath = file_manager.save_data_to_json(email_reports, output_filename_base)
        if saved_filepath:
            print(f"Successfully saved {len(email_reports)} news reports to {saved_filepath}")
        else:
            print("Error: Failed to save the news reports.")
    else:
        print("Info: No news reports were generated to save.")
        
    # Export the compiled news reports to Google Doc
    if email_reports and saved_filepath:
        print("\n--- Exporting News Reports to Google Doc ---")
        
        gdoc_url = google_docs_exporter.update_or_create_news_document(school_config.SCHOOL_PROFILES["nyu"], email_reports, breaking_news_date, breaking_news_date)
        if gdoc_url:
            print(f"Successfully operated on Google Doc: {gdoc_url}")
        else:
            print("Error: Failed to operate on Google Doc.")
            print("Ensure Google Docs API is enabled, OAuth credentials correct, and app authorized.")
    elif not email_reports:
        print("Info: No reports to export to Google Doc.")

if __name__ == "__main__":
    orchestrate_breaking_news()