# app.py - Flask Web Interface for Project NEXUS News Bot

import sys
import traceback

# Add startup logging
print("="* 60, file=sys.stderr)
print("🚀 NEXUS: Starting Flask app import...", file=sys.stderr)
print("="* 60, file=sys.stderr)

try:
    from flask import Flask, render_template, request, jsonify, Response, send_file
    print("✅ Flask imported successfully", file=sys.stderr)
except Exception as e:
    print(f"❌ Failed to import Flask: {e}", file=sys.stderr)
    traceback.print_exc()
    raise

try:
    from datetime import datetime, date, timedelta
    from pathlib import Path
    import json
    import os
    import threading
    from queue import Queue
    import zipfile
    import tempfile
    import shutil
    print("✅ Standard library modules imported", file=sys.stderr)
except Exception as e:
    print(f"❌ Failed to import standard library: {e}", file=sys.stderr)
    traceback.print_exc()
    raise

try:
    from news_bot.core import config, school_config
    print("✅ Config modules imported", file=sys.stderr)
except Exception as e:
    print(f"❌ Failed to import config: {e}", file=sys.stderr)
    traceback.print_exc()
    raise

try:
    from news_bot.discovery import search_client
    from news_bot.processing import article_handler
    from news_bot.generation import summarizer
    from news_bot.utils import file_manager, prompt_logger
    from news_bot.localization import translator
    print("✅ News bot modules imported successfully", file=sys.stderr)
except Exception as e:
    print(f"❌ Failed to import news bot modules: {e}", file=sys.stderr)
    traceback.print_exc()
    raise

print("✅ All imports successful - creating Flask app...", file=sys.stderr)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'nexus-news-bot-secret-key')
print("✅ Flask app created successfully", file=sys.stderr)
print(f"📦 App name: {app.name}", file=sys.stderr)
print(f"📁 Root path: {app.root_path}", file=sys.stderr)

# Basic health check route (must be defined early, before any config imports fail)
@app.route('/health')
@app.route('/healthz')  # Common k8s/Railway health check path
def health_check():
    """Railway health check endpoint - doesn't depend on config."""
    return jsonify({
        'status': 'healthy',
        'service': 'NEXUS News Bot',
        'timestamp': datetime.now().isoformat(),
        'routes': len(app.url_map._rules)
    }), 200, {'Content-Type': 'application/json'}

# Simple ping endpoint (ultra-lightweight)
@app.route('/ping')
def ping():
    """Ultra-simple ping endpoint for load balancer health checks."""
    return 'pong', 200, {'Content-Type': 'text/plain'}

# Directory creation moved to route handlers to avoid blocking during import
# Railway needs the app to import quickly so health check can respond

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
        
        # Temporarily override config date range for entire processing
        # This ensures discovery, verification, and all date checks use user-selected dates
        original_start_date = config.NEWS_START_DATE
        original_threshold = config.RECENCY_THRESHOLD_DAYS
        try:
            # Override config with user-selected dates
            config.NEWS_START_DATE = start_date
            config.RECENCY_THRESHOLD_DAYS = (end_date - start_date).days + 1
            
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
                    "school_name": chosen_school['school_name'],
                    "school_id": school_id,
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
                    send_progress(f"✅ Saved {len(final_news_reports)} reports to JSON", 95)
            
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
        
        finally:
            # Restore original config after all processing is complete
            config.NEWS_START_DATE = original_start_date
            config.RECENCY_THRESHOLD_DAYS = original_threshold
        
    except Exception as e:
        current_job_status['error'] = str(e)
        send_progress(f"❌ Error: {e}", current_job_status['progress'])
    finally:
        current_job_status['running'] = False

@app.route('/')
def index():
    """Render the main page."""
    try:
        # Ensure output directory exists (lazy initialization)
        os.makedirs(config.DEFAULT_OUTPUT_DIR, exist_ok=True)
        
        schools = school_config.SCHOOL_PROFILES
        start_date, end_date = config.get_news_date_range()
        
        return render_template('index.html', 
                             schools=schools,
                             default_start_date=start_date.isoformat(),
                             default_end_date=end_date.isoformat(),
                             max_reports=config.MAX_FINAL_REPORTS)
    except Exception as e:
        # Graceful fallback if config fails
        print(f"❌ Error loading index: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        
        # Return a simple error page that loads fast
        return f"""<!DOCTYPE html>
<html>
<head>
    <title>NEXUS - Configuration Error</title>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, sans-serif; padding: 40px; max-width: 800px; margin: 0 auto; }}
        code {{ background: #f4f4f4; padding: 2px 6px; border-radius: 3px; }}
        .error {{ color: #d32f2f; }}
    </style>
</head>
<body>
    <h1>⚠️ Configuration Error</h1>
    <p>The application failed to load its configuration.</p>
    <p class="error"><strong>Error:</strong> {str(e)[:200]}</p>
    <h2>Troubleshooting Steps:</h2>
    <ol>
        <li>Ensure <code>OPENROUTER_API_KEY</code> is set in Railway Variables</li>
        <li>Check Railway logs for detailed error messages</li>
        <li>Verify all environment variables are configured</li>
    </ol>
    <p><a href="/health">Health Check</a> | <a href="/api/debug/chromium">Chromium Debug</a></p>
</body>
</html>""", 500

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
    try:
        # Ensure output directory exists
        os.makedirs(config.DEFAULT_OUTPUT_DIR, exist_ok=True)
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
    except Exception as e:
        print(f"Error in list_reports: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e), 'reports': []}), 500

@app.route('/api/reports/<filename>', methods=['GET'])
def get_report(filename):
    """Get a specific report."""
    try:
        # Sanitize filename to prevent directory traversal
        filename = os.path.basename(filename)
        filepath = os.path.join(config.DEFAULT_OUTPUT_DIR, filename)
        
        if not os.path.exists(filepath):
            return jsonify({'error': 'Report not found'}), 404
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return jsonify(data)
    except Exception as e:
        print(f"Error in get_report: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/save-report', methods=['POST'])
def save_report():
    """Save edited report data back to JSON file."""
    data = request.json
    report_filename = data.get('report_filename')
    report_data = data.get('report_data')
    
    if not report_filename or not report_data:
        return jsonify({'error': 'Report filename and data are required'}), 400
    
    report_path = Path(config.DEFAULT_OUTPUT_DIR) / report_filename
    
    try:
        # Save the edited data
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        return jsonify({
            'success': True,
            'message': 'Report saved successfully'
        })
    except Exception as e:
        return jsonify({
            'error': 'Failed to save report',
            'details': str(e)
        }), 500

@app.route('/api/ai-edit', methods=['POST'])
def ai_edit_text():
    """Use AI to edit text based on user prompt."""
    data = request.json
    text = data.get('text', '')
    prompt = data.get('prompt', '')
    article_index = data.get('article_index', None)
    
    if not text or not prompt:
        return jsonify({'error': 'Text and prompt are required'}), 400
    
    try:
        from news_bot.utils.openrouter_client import generate_content
        
        # Create a comprehensive prompt for editing
        edit_prompt = f"""You are a professional Chinese news editor. The user wants you to edit the following Chinese news text.

User's request: {prompt}

Original text:
{text}

Please provide ONLY the edited text, without any explanations or additional comments. Return the complete edited text that addresses the user's request."""
        
        edited_text = generate_content(edit_prompt, temperature=0.7)
        
        if not edited_text:
            return jsonify({
                'error': 'Failed to get AI response',
                'details': 'OpenRouter API returned no content'
            }), 500
        
        return jsonify({
            'success': True,
            'edited_text': edited_text.strip()
        })
        
    except Exception as e:
        return jsonify({
            'error': 'Failed to edit text with AI',
            'details': str(e)
        }), 500

@app.route('/api/generate-images', methods=['POST'])
def generate_wechat_images():
    """Generate WeChat-style images directly from JSON report (no Google Docs needed)."""
    data = request.json
    report_filename = data.get('report_filename')
    report_data = data.get('report_data')  # Optional: use edited data instead of file
    
    if not report_filename:
        return jsonify({'error': 'Report filename is required'}), 400
    
    report_path = Path(config.DEFAULT_OUTPUT_DIR) / report_filename
    
    # If edited data provided, save it temporarily
    if report_data:
        temp_path = Path(tempfile.mkdtemp()) / report_filename
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        json_path = str(temp_path)
    else:
        if not report_path.exists():
            return jsonify({'error': f'Report file not found: {report_filename}'}), 404
        json_path = str(report_path)
    
    try:
        # Import the direct JSON to images converter
        from scripts.json_to_wechat_images import json_to_wechat_images
        
        # Try to get school from report data for explicit school parameter
        school_name = None
        if report_data and isinstance(report_data, list) and len(report_data) > 0:
            school_name = report_data[0].get('school_name')
        elif report_path.exists():
            # Load from file to get school name
            with open(report_path, 'r', encoding='utf-8') as f:
                file_data = json.load(f)
                if file_data and len(file_data) > 0:
                    school_name = file_data[0].get('school_name')
        
        # Generate images directly from JSON
        result = json_to_wechat_images(
            json_path=json_path,
            output_base_dir='wechat_images',
            page_width=540,
            device_scale=4,
            title_size=22.093076923,
            body_size=20.0,
            top_n_sources=10,
            school_override=school_name,  # Pass explicit school if available
        )
        
        # Clean up temp file if used
        if report_data and temp_path.exists():
            temp_path.unlink()
            temp_path.parent.rmdir()
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': f'Generated {result["total_images"]} WeChat-style images',
                'output_dir': result['output_dir'],
                'school': result['school'],
                'brand_color': result['brand_color'],
                'total_images': result['total_images'],
                'files': result['generated_files'],
            })
        else:
            return jsonify({
                'error': result.get('error', 'Unknown error'),
            }), 500
        
    except ImportError as e:
        return jsonify({
            'error': 'Image generation module not available',
            'details': str(e),
            'note': 'Make sure pyppeteer is installed: pip install pyppeteer'
        }), 500
    except Exception as e:
        return jsonify({
            'error': 'Failed to generate images',
            'details': str(e)
        }), 500

@app.route('/api/download-images/<path:output_dir>', methods=['GET'])
def download_images_zip(output_dir):
    """Download generated images as a ZIP file."""
    try:
        # Sanitize path to prevent directory traversal
        safe_dir = output_dir.replace('..', '').replace('/', os.sep).replace('\\', os.sep)
        images_dir = Path('wechat_images') / safe_dir
        
        if not images_dir.exists() or not images_dir.is_dir():
            return jsonify({'error': 'Images directory not found'}), 404
        
        # Create temporary ZIP file
        temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
        temp_zip_path = temp_zip.name
        temp_zip.close()
        
        # Create ZIP archive
        with zipfile.ZipFile(temp_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for image_file in images_dir.glob('*.png'):
                zipf.write(image_file, image_file.name)
        
        # Send ZIP file
        return send_file(
            temp_zip_path,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f'{safe_dir}_images.zip'
        )
        
    except Exception as e:
        return jsonify({
            'error': 'Failed to create ZIP file',
            'details': str(e)
        }), 500

@app.route('/api/debug/chromium', methods=['GET'])
def debug_chromium():
    """Debug endpoint to check Chromium installation (Railway troubleshooting)."""
    import subprocess
    import glob
    
    result = {
        'timestamp': datetime.now().isoformat(),
        'platform': os.name,
        'environment': {}
    }
    
    # Check environment variables
    for key in ['PUPPETEER_EXECUTABLE_PATH', 'CHROME_PATH', 'PATH']:
        result['environment'][key] = os.environ.get(key, 'Not set')
    
    # Check if chromium is in PATH
    chromium_which = shutil.which('chromium')
    chromium_browser_which = shutil.which('chromium-browser')
    chrome_which = shutil.which('google-chrome')
    
    result['executables'] = {
        'chromium': chromium_which,
        'chromium-browser': chromium_browser_which,
        'google-chrome': chrome_which,
    }
    
    # Check Nix store (Railway/Nixpacks)
    try:
        nix_chromium = glob.glob('/nix/store/*/bin/chromium')
        result['nix_store_chromium'] = nix_chromium if nix_chromium else 'Not found'
    except Exception as e:
        result['nix_store_chromium'] = f'Error: {e}'
    
    # Try to get Chromium version
    for cmd in ['chromium', 'chromium-browser', 'google-chrome']:
        try:
            proc = subprocess.run(
                [cmd, '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            result[f'{cmd}_version'] = proc.stdout.strip()
            break
        except Exception as e:
            result[f'{cmd}_version'] = f'Error: {e}'
    
    # Test image generator's auto-detection
    try:
        from news_bot.processing.image_generator import _guess_chrome_path
        detected_path = _guess_chrome_path()
        result['auto_detected_path'] = detected_path if detected_path else 'None'
        
        if detected_path:
            result['auto_detected_exists'] = Path(detected_path).exists()
    except Exception as e:
        result['auto_detection_error'] = str(e)
    
    return jsonify(result)

# Module loaded successfully
print("="* 60, file=sys.stderr)
print("✅ NEXUS Flask app fully loaded - ready for requests", file=sys.stderr)
print(f"📝 Total routes registered: {len(app.url_map._rules)}", file=sys.stderr)
print("="* 60, file=sys.stderr)

if __name__ == '__main__':
    # Ensure output directory exists
    os.makedirs(config.DEFAULT_OUTPUT_DIR, exist_ok=True)
    
    # Get port from environment (Railway provides this) or default to 5000
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV', 'development') != 'production'
    
    print("=" * 60)
    print("🚀 Project NEXUS - News Bot Web Interface")
    print("=" * 60)
    print(f"📊 Dashboard: http://0.0.0.0:{port}")
    print(f"📁 Output Directory: {config.DEFAULT_OUTPUT_DIR}")
    print(f"🔧 Environment: {os.environ.get('FLASK_ENV', 'development')}")
    print("=" * 60)
    
    # Bind to 0.0.0.0 for Railway deployment
    app.run(host='0.0.0.0', port=port, debug=debug, threaded=True)

