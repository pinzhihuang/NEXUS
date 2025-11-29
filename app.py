# app.py - Flask Web Interface for Project NEXUS News Bot

from flask import Flask, render_template, request, jsonify, Response
from datetime import datetime, date, timedelta
import json
import os
import threading
from queue import Queue

from news_bot.core import config, school_config
from news_bot.discovery import search_client
from news_bot.processing import article_handler
from news_bot.generation import summarizer
from news_bot.utils import file_manager, prompt_logger
from news_bot.localization import translator
from news_bot.reporting import google_docs_exporter

app = Flask(__name__)
app.config['SECRET_KEY'] = 'nexus-news-bot-secret-key'

# Global queue for progress updates
progress_queue = Queue()
current_job_status = {
    'running': False,
    'progress': 0,
    'current_step': '',
    'articles_found': 0,
    'articles_processed': 0,
    'reports_generated': 0,
    'error': None
}

def send_progress(message, progress=None):
    """Send progress update to the queue."""
    global current_job_status
    
    if progress is not None:
        current_job_status['progress'] = progress
    
    current_job_status['current_step'] = message
    
    update = {
        'message': message,
        'progress': current_job_status['progress'],
        'articles_found': current_job_status['articles_found'],
        'articles_processed': current_job_status['articles_processed'],
        'reports_generated': current_job_status['reports_generated'],
        'timestamp': datetime.now().isoformat()
    }
    
    progress_queue.put(json.dumps(update))

def run_news_bot_async(school_id, start_date_str, end_date_str, max_reports):
    """Run the news bot in a background thread."""
    global current_job_status
    
    try:
        current_job_status['running'] = True
        current_job_status['error'] = None
        current_job_status['progress'] = 0
        
        send_progress("🚀 Initializing Project NEXUS News Bot...", 5)
        
        # Validate configuration
        try:
            config.validate_config()
        except ValueError as e:
            current_job_status['error'] = str(e)
            send_progress(f"❌ Configuration Error: {e}", 0)
            current_job_status['running'] = False
            return
        
        send_progress("✅ Configuration validated", 10)
        
        # Get selected school
        schools_list = list(school_config.SCHOOL_PROFILES.values())
        chosen_school = schools_list[school_id - 1]
        
        send_progress(f"🎓 Selected: {chosen_school['school_name']}", 15)
        
        # Parse date range
        if start_date_str and end_date_str:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        else:
            start_date, end_date = config.get_news_date_range()
        
        send_progress(f"📅 Date range: {start_date} to {end_date}", 20)
        
        # Step 1: Discover articles
        send_progress("🔍 Discovering articles from news sources...", 25)
        prompt_log_file = prompt_logger.initialize_prompt_log()
        
        discovered_articles = search_client.find_relevant_articles(chosen_school)
        
        if not discovered_articles:
            send_progress("ℹ️ No articles discovered. Job completed.", 100)
            current_job_status['running'] = False
            return
        
        current_job_status['articles_found'] = len(discovered_articles)
        send_progress(f"✅ Found {len(discovered_articles)} potential articles", 30)
        
        # Process articles
        final_news_reports = []
        processed_urls = set()
        articles_to_process = min(len(discovered_articles), max_reports)
        
        send_progress(f"⚙️ Processing articles (max: {max_reports})...", 35)
        
        for i, article_info in enumerate(discovered_articles):
            if len(final_news_reports) >= max_reports:
                send_progress(f"✅ Reached maximum number of reports ({max_reports})", 90)
                break
            
            progress = 35 + (50 * (i + 1) / articles_to_process)
            
            original_title = article_info.get("title", "N/A")
            article_url = article_info.get("url")
            source_method = article_info.get("source_method", "Unknown")
            article_date = article_info.get("url_date", "N/A")
            
            current_job_status['articles_processed'] = i + 1
            send_progress(f"📰 Processing: {original_title[:50]}...", progress)
            
            if not article_url or not article_url.startswith("http"):
                continue
            
            if article_url in processed_urls:
                continue
            processed_urls.add(article_url)
            
            # Fetch and extract text
            article_text = article_handler.fetch_and_extract_text(article_url)
            if not article_text:
                continue
            
            # Verify article
            verification_results = article_handler.verify_article_with_gemini(
                chosen_school, article_text, article_url, article_date
            )
            if not verification_results:
                continue
            
            # Check if suitable for summary
            is_within_date_range = verification_results.get("is_within_range", False)
            if not is_within_date_range:
                is_within_date_range = "Within range" in verification_results.get("is_recent", "") or "Recent" in verification_results.get("is_recent", "")
            
            allow_events = bool(chosen_school.get("include_event_announcements"))
            article_type = verification_results.get("article_type_assessment")
            allow_opinion = bool(chosen_school.get("include_opinion_blog"))
            
            is_suitable_for_summary = (
                is_within_date_range and
                verification_results.get("is_relevant") == "Relevant" and
                (
                    article_type == "News article" or
                    (allow_events and article_type == "Event/Announcement") or
                    (allow_opinion and article_type == "Opinion/Blog")
                )
            )
            
            if not is_suitable_for_summary:
                continue
            
            send_progress(f"✍️ Generating summary for: {original_title[:40]}...", progress)
            
            # Generate English summary
            english_summary = summarizer.generate_summary_with_gemini(
                chosen_school, article_text, article_url, original_title
            )
            if not english_summary or "failed" in english_summary.lower():
                continue
            
            send_progress(f"🌏 Translating to Chinese...", progress)
            
            # Translate to Chinese
            english_report_data = {
                "summary": english_summary,
                "source_url": article_url,
                "reported_publication_date": verification_results.get("publication_date_str", "N/A"),
                "original_title": original_title
            }
            translation_output = translator.translate_and_restyle_to_chinese(english_report_data)
            
            chinese_title = "中文标题失败"
            refined_chinese_report = "翻译失败"
            
            if translation_output:
                chinese_title = translation_output.get("chinese_title", chinese_title)
                refined_chinese_report = translation_output.get("refined_chinese_news_report", refined_chinese_report)
            
            final_news_reports.append({
                "news_id": len(final_news_reports) + 1,
                "original_title": original_title,
                "source_url": article_url,
                "source_method": source_method,
                "reported_publication_date": verification_results.get("publication_date_str", "N/A"),
                "verification_details": verification_results,
                "english_summary": english_summary,
                "chinese_title": chinese_title,
                "refined_chinese_news_report": refined_chinese_report,
                "processing_timestamp": datetime.now().isoformat()
            })
            
            current_job_status['reports_generated'] = len(final_news_reports)
        
        # Save reports
        send_progress("💾 Saving news reports...", 85)
        
        if final_news_reports:
            output_filename_base = f"weekly_student_news_report_{start_date}_{end_date}"
            saved_filepath = file_manager.save_data_to_json(final_news_reports, output_filename_base)
            
            if saved_filepath:
                send_progress(f"✅ Saved {len(final_news_reports)} reports to JSON", 90)
            
            # Export to Google Doc
            send_progress("📄 Exporting to Google Docs...", 95)
            gdoc_url = google_docs_exporter.update_or_create_news_document(
                chosen_school, final_news_reports, start_date, end_date
            )
            
            if gdoc_url:
                send_progress(f"✅ Google Doc created: {gdoc_url}", 98)
            
            # Write footer to prompt log
            if prompt_log_file:
                try:
                    with open(prompt_log_file, 'a', encoding='utf-8') as f:
                        f.write("\n" + "=" * 80 + "\n")
                        f.write(f"Run completed: {datetime.now().isoformat()}\n")
                        f.write(f"Date Range: {start_date} to {end_date}\n")
                        f.write(f"Total Reports: {len(final_news_reports)}\n")
                        f.write("=" * 80 + "\n")
                except Exception as e:
                    pass
            
            send_progress(f"🎉 Complete! Generated {len(final_news_reports)} news reports", 100)
        else:
            send_progress("ℹ️ No suitable articles found for reporting", 100)
        
    except Exception as e:
        current_job_status['error'] = str(e)
        send_progress(f"❌ Error: {e}", current_job_status['progress'])
    finally:
        current_job_status['running'] = False

@app.route('/')
def index():
    """Render the main page."""
    schools = school_config.SCHOOL_PROFILES
    start_date, end_date = config.get_news_date_range()
    
    return render_template('index.html', 
                         schools=schools,
                         default_start_date=start_date.isoformat(),
                         default_end_date=end_date.isoformat(),
                         max_reports=config.MAX_FINAL_REPORTS)

@app.route('/api/config', methods=['GET'])
def get_config():
    """Get current configuration."""
    start_date, end_date = config.get_news_date_range()
    
    return jsonify({
        'schools': [
            {
                'id': info['id'],
                'key': key,
                'name': info['school_name'],
                'location': info['school_location']
            }
            for key, info in school_config.SCHOOL_PROFILES.items()
        ],
        'date_range': {
            'start': start_date.isoformat(),
            'end': end_date.isoformat(),
            'days': config.RECENCY_THRESHOLD_DAYS
        },
        'max_reports': config.MAX_FINAL_REPORTS,
        'is_configured': bool(config.OPENROUTER_API_KEY)
    })

@app.route('/api/start', methods=['POST'])
def start_job():
    """Start a news collection job."""
    global current_job_status
    
    if current_job_status['running']:
        return jsonify({'error': 'A job is already running'}), 400
    
    data = request.json
    school_id = data.get('school_id', 1)
    start_date = data.get('start_date', None)
    end_date = data.get('end_date', None)
    max_reports = data.get('max_reports', config.MAX_FINAL_REPORTS)
    
    # Reset status
    current_job_status = {
        'running': True,
        'progress': 0,
        'current_step': 'Starting...',
        'articles_found': 0,
        'articles_processed': 0,
        'reports_generated': 0,
        'error': None
    }
    
    # Clear the queue
    while not progress_queue.empty():
        progress_queue.get()
    
    # Start background thread
    thread = threading.Thread(
        target=run_news_bot_async,
        args=(school_id, start_date, end_date, max_reports)
    )
    thread.daemon = True
    thread.start()
    
    return jsonify({'message': 'Job started successfully'})

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get current job status."""
    return jsonify(current_job_status)

@app.route('/api/progress')
def progress_stream():
    """Server-Sent Events endpoint for real-time progress updates."""
    def generate():
        while True:
            message = progress_queue.get()
            yield f"data: {message}\n\n"
    
    return Response(generate(), mimetype='text/event-stream')

@app.route('/api/reports', methods=['GET'])
def list_reports():
    """List all generated reports."""
    reports_dir = config.DEFAULT_OUTPUT_DIR
    
    if not os.path.exists(reports_dir):
        return jsonify({'reports': []})
    
    reports = []
    for filename in os.listdir(reports_dir):
        if filename.endswith('.json'):
            filepath = os.path.join(reports_dir, filename)
            stat = os.stat(filepath)
            reports.append({
                'filename': filename,
                'size': stat.st_size,
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'url': f'/api/reports/{filename}'
            })
    
    reports.sort(key=lambda x: x['modified'], reverse=True)
    return jsonify({'reports': reports})

@app.route('/api/reports/<filename>', methods=['GET'])
def get_report(filename):
    """Get a specific report."""
    filepath = os.path.join(config.DEFAULT_OUTPUT_DIR, filename)
    
    if not os.path.exists(filepath):
        return jsonify({'error': 'Report not found'}), 404
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return jsonify(data)

if __name__ == '__main__':
    # Ensure output directory exists
    os.makedirs(config.DEFAULT_OUTPUT_DIR, exist_ok=True)
    
    print("=" * 60)
    print("🚀 Project NEXUS - News Bot Web Interface")
    print("=" * 60)
    print(f"📊 Dashboard: http://127.0.0.1:5000")
    print(f"📁 Output Directory: {config.DEFAULT_OUTPUT_DIR}")
    print("=" * 60)
    
    app.run(debug=True, threaded=True, port=5000)

