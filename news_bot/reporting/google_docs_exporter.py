# news_bot/reporting/google_docs_exporter.py

import os.path
import pickle # For storing/loading OAuth tokens
from datetime import datetime, timedelta # Import timedelta for date calculations

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from ..core import config # For credentials paths and scopes

def _get_credentials():
    """
    Gets valid user credentials from storage or initiates OAuth2 flow.
    The file token.pickle stores the user's access and refresh tokens, and is
    created automatically when the authorization flow completes for the first time.
    """
    creds = None
    if os.path.exists(config.OAUTH_TOKEN_PICKLE_FILE):
        with open(config.OAUTH_TOKEN_PICKLE_FILE, 'rb') as token:
            creds = pickle.load(token)
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                print("Refreshing OAuth token...")
                creds.refresh(Request())
            except Exception as e_refresh:
                print(f"Error refreshing token: {e_refresh}. Need to re-authorize.")
                creds = None # Force re-authorization
        if not creds: # creds might be None if refresh failed or no token.pickle
            if not os.path.exists(config.OAUTH_CREDENTIALS_FILE):
                print(f"Error: OAuth credentials.json not found at {config.OAUTH_CREDENTIALS_FILE}")
                print("Please download it from Google Cloud Console and place it in the project root.")
                return None
            try:
                print("Initiating OAuth flow for Google Docs... Please follow browser instructions.")
                flow = InstalledAppFlow.from_client_secrets_file(
                    config.OAUTH_CREDENTIALS_FILE, config.GOOGLE_DOCS_SCOPES)
                creds = flow.run_local_server(port=0)
            except Exception as e_flow:
                print(f"Error during OAuth flow: {e_flow}")
                return None
        
        # Save the credentials for the next run
        if creds:
            try:
                with open(config.OAUTH_TOKEN_PICKLE_FILE, 'wb') as token:
                    pickle.dump(creds, token)
                print(f"OAuth token saved to {config.OAUTH_TOKEN_PICKLE_FILE}")
            except Exception as e_save_token:
                print(f"Error saving OAuth token: {e_save_token}")
        else:
            print("Failed to obtain OAuth credentials.")
            return None # Explicitly return None if creds are still None
            
    return creds

def update_or_create_news_document(reports_data: list, week_start_date: datetime.date, week_end_date: datetime.date) -> str | None:
    """
    Updates a specific Google Doc (if ID is configured) or creates a new one.
    Populates it with the refined Chinese news reports and a main weekly header.

    Args:
        reports_data: A list of news report dictionaries.
        week_start_date: The start date of the news week.
        week_end_date: The end date of the news week.

    Returns:
        The URL of the Google Document, or None if an error occurs.
    """
    creds = _get_credentials()
    if not creds:
        print("Error: Could not get Google API credentials. Cannot operate on Google Doc.")
        return None

    doc_id_to_update = config.TARGET_GOOGLE_DOC_ID
    doc_url = None
    service = None

    try:
        service = build('docs', 'v1', credentials=creds)
        document_title = f"Project NEXUS: Weekly Chinese News Digest ({week_start_date.strftime('%m/%d')} - {week_end_date.strftime('%m/%d/%Y')})"

        if doc_id_to_update:
            print(f"Attempting to update existing Google Doc ID: {doc_id_to_update}")
            try:
                doc = service.documents().get(documentId=doc_id_to_update).execute()
                print(f"Found existing document: '{doc.get('title')}'. Clearing content...")
                
                content_elements = doc.get('body', {}).get('content', [])
                start_delete_index = 1 # Body content usually starts at index 1
                end_delete_index = 1

                if content_elements:
                    # Find the endIndex of the very last element in the body that is not the implicit first paragraph.
                    # The document body.content is a list of StructuralElement.
                    # The first element (index 0 in this list) often corresponds to the first paragraph.
                    # We usually want to delete content *after* this potential initial paragraph if it exists.
                    # If the list has only one element, it might be an empty doc or just one paragraph.
                    if len(content_elements) > 0: # Check if there are any elements at all
                        # The actual content we want to clear often starts effectively at index 1 of the document, 
                        # or at the startIndex of the first element if there's only one, or second if more.
                        # Let's target the end of all current body content.
                        last_content_element = content_elements[-1]
                        end_delete_index = last_content_element.get('endIndex', 1)
                    
                # Delete content only if there's a valid range (more than just the implicit start)
                if end_delete_index > start_delete_index:
                    # Adjust endIndex to avoid deleting the newline at the very end of the segment
                    range_to_delete_end_index = end_delete_index - 1
                    
                    # Ensure startIndex is not greater than or equal to the adjusted endIndex
                    if start_delete_index < range_to_delete_end_index:
                        clear_requests = [
                            {
                                'deleteContentRange': {
                                    'range': {
                                        'startIndex': start_delete_index,
                                        'endIndex': range_to_delete_end_index 
                                    }
                                }
                            }
                        ]
                        service.documents().batchUpdate(documentId=doc_id_to_update, body={'requests': clear_requests}).execute()
                        print(f"Cleared content from index {start_delete_index} to {range_to_delete_end_index}.")
                    else:
                        print("Info: Document content range too small to clear safely after adjustment, or already effectively empty.")
                else:
                    print("Info: Document body seems empty or too short to clear.")
                doc_url = f"https://docs.google.com/document/d/{doc_id_to_update}/edit"
            except HttpError as e_get_doc:
                if e_get_doc.resp.status == 404:
                    print(f"Error: Target Google Doc ID '{doc_id_to_update}' not found. Will create a new document.")
                    doc_id_to_update = None # Fallback to creating a new one
                else:
                    raise # Re-raise other HttpErrors
        
        if not doc_id_to_update: # Create new if no ID or target was not found
            print(f"Creating new Google Doc titled: '{document_title}'...")
            doc_body_create = {'title': document_title}
            doc = service.documents().create(body=doc_body_create).execute()
            doc_id_to_update = doc.get('documentId')
            doc_url = f"https://docs.google.com/document/d/{doc_id_to_update}/edit"
            print(f"New Google Doc created with ID: {doc_id_to_update} (URL: {doc_url})")

        # --- Construct content requests --- 
        requests_body = []
        current_offset = 1 

        # 1. Add Main Weekly Header
        main_header_text = f"本周新闻摘要 (News Digest): {week_start_date.strftime('%Y年%m月%d日')} - {week_end_date.strftime('%Y年%m月%d日')}\n\n"
        requests_body.append({
            'insertText': {
                'location': {'index': current_offset},
                'text': main_header_text
            }
        })
        requests_body.append({
            'updateParagraphStyle': {
                'range': {
                    'startIndex': current_offset,
                    'endIndex': current_offset + len(main_header_text) -1 
                },
                'paragraphStyle': {
                    'namedStyleType': 'TITLE' # Using 'TITLE' style for main header
                },
                'fields': 'namedStyleType'
            }
        })
        current_offset += len(main_header_text)

        # 2. Add Individual News Reports
        for i, report in enumerate(reports_data):
            chinese_title = report.get('chinese_title', '无标题')
            refined_report = report.get('refined_chinese_news_report', '内容缺失')
            source_url = report.get('source_url', '#')

            if i > 0: # Add separator before second article onwards
                requests_body.append({'insertText': {'location': {'index': current_offset}, 'text': '\n---\n\n'}})
                current_offset += 5

            title_text = f"{chinese_title}\n"
            requests_body.append({'insertText': {'location': {'index': current_offset}, 'text': title_text}})
            requests_body.append({
                'updateParagraphStyle': {
                    'range': {'startIndex': current_offset, 'endIndex': current_offset + len(title_text) -1},
                    'paragraphStyle': {'namedStyleType': 'HEADING_1'},
                    'fields': 'namedStyleType'
                }
            })
            current_offset += len(title_text)

            report_body_text = f"{refined_report}\n"
            requests_body.append({'insertText': {'location': {'index': current_offset}, 'text': report_body_text}})
            current_offset += len(report_body_text)

            source_line_text = f"来源 (Source): {source_url}\n\n"
            requests_body.append({'insertText': {'location': {'index': current_offset}, 'text': source_line_text}})
            url_start_idx = source_line_text.find(source_url)
            if url_start_idx != -1:
                requests_body.append({
                    'updateTextStyle': {
                        'range': {'startIndex': current_offset + url_start_idx, 'endIndex': current_offset + url_start_idx + len(source_url)},
                        'textStyle': {'link': {'url': source_url}},
                        'fields': 'link'
                    }
                })
            current_offset += len(source_line_text)

        if requests_body:
            print(f"Writing {len(reports_data)} reports to Google Doc ID: {doc_id_to_update}...")
            service.documents().batchUpdate(documentId=doc_id_to_update, body={'requests': requests_body}).execute()
            print("Content successfully written to Google Doc.")
        else:
            print("No reports to write to Google Doc.")
        return doc_url

    except HttpError as err:
        print(f"An HTTP error occurred with Google Docs API: {err.resp.status} - {err._get_reason()}")
        if err.resp.status == 403:
            print("This might be due to the Google Docs API not being enabled, or incorrect OAuth scopes/permissions.")
            print(f"Ensure correct scopes are used: {config.GOOGLE_DOCS_SCOPES}")
        elif err.resp.status == 401:
            print("Authentication error. Token might be invalid/expired. Try deleting token.pickle and re-authorizing.")
        return None # Make sure to return None on HttpError
    except Exception as e:
        print(f"An unexpected error occurred with Google Docs exporter: {e}")
        return None # Make sure to return None on other exceptions
    
if __name__ == '__main__':
    print("Testing Google Docs Exporter (Update/Create Mode)...")
    import sys
    PROJECT_ROOT_FOR_TEST = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if PROJECT_ROOT_FOR_TEST not in sys.path:
         sys.path.insert(0, PROJECT_ROOT_FOR_TEST)
    
    from news_bot.core import config # Re-import for paths
    # config.validate_config() # Not strictly needed for this test if paths are correct
    if not os.path.exists(config.OAUTH_CREDENTIALS_FILE):
        print(f"STOPPING TEST: {config.OAUTH_CREDENTIALS_FILE} not found. Please download it for OAuth flow.")
    else:
        print(f"Using credentials file: {config.OAUTH_CREDENTIALS_FILE}")
        print(f"Token file will be: {config.OAUTH_TOKEN_PICKLE_FILE}")
        if config.TARGET_GOOGLE_DOC_ID:
            print(f"Will attempt to update Target Google Doc ID: {config.TARGET_GOOGLE_DOC_ID}")
        else:
            print("No Target Google Doc ID set in config, will create a new document.")
        
        # Corrected string literals for sample_reports using triple quotes
        sample_reports = [
            {
                "chinese_title": """纽约大学启动新的国际学生签证援助项目""",
                "refined_chinese_news_report": """据NYU官网报道，2024年5月21日消息：纽约大学（New York University）今日启动一项新签证支持项目，旨在帮助国际学生应对近期美国签证申请流程的变化。该项目详情已在纽约大学全球服务办公室网站公布，内容包括专题研讨会、延长咨询服务时间及新设的在线文件提交门户。此前，包括来自中国的多名学生反映，签证审查日趋严格，且时有延误。校长琳达·G·米尔斯（Linda G. Mills）重申："纽约大学致力于维护其全球化社区，我们将提供一切必要资源，协助国际学生处理这些复杂问题。" 此举预计将惠及数百名准备迎接新学年的学生。""",
                "source_url": """https://www.nyu.edu/news/2024/05/21/visa-support-initiative.html"""
            },
            {
                "chinese_title": """华盛顿广场新闻：学生会选举动态更新""",
                "refined_chinese_news_report": """据WSN报道，2024年5月20日消息：华盛顿广场新闻（Washington Square News）报道了最新学生会选举进展。候选人李明（John Doe）就校园住宿问题发表了看法。选举最终结果预计下周揭晓。""",
                "source_url": """https://nyunews.com/news/2024/05/20/student-elections/"""
            }
        ]
        
        # For testing, let's define a sample week range
        test_week_end_date = datetime.now().date()
        test_week_start_date = test_week_end_date - timedelta(days=6)

        doc_link = update_or_create_news_document(sample_reports, test_week_start_date, test_week_end_date)

        if doc_link:
            print(f"\nSuccessfully operated on Google Doc: {doc_link}")
        else:
            print("\nFailed to operate on Google Doc.") 