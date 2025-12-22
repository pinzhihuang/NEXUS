# app.py - Flask Web Interface for Project NEXUS News Bot

import sys
import traceback
import logging

# ============================================================================
# ENHANCED LOGGING SETUP
# ============================================================================
# Configure logging to capture all levels and output to stderr
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stderr)
    ]
)

# Create loggers for different modules
logger = logging.getLogger('app')
logger_discovery = logging.getLogger('discovery')
logger_processing = logging.getLogger('processing')
logger_generation = logging.getLogger('generation')
logger_translation = logging.getLogger('translation')

logger.info("=" * 60)
logger.info("🚀 NEXUS: Starting Flask app import...")
logger.info("=" * 60)

try:
    from flask import Flask, render_template, request, jsonify, Response, send_file
    logger.info("✅ Flask imported successfully")
except Exception as e:
    logger.error(f"❌ Failed to import Flask: {e}")
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
    import time
    logger.info("✅ Standard library modules imported")
except Exception as e:
    logger.error(f"❌ Failed to import standard library: {e}")
    traceback.print_exc()
    raise

try:
    from news_bot.core import config, school_config
    logger.info("✅ Config modules imported")
    logger.debug(f"  - DEFAULT_OUTPUT_DIR: {config.DEFAULT_OUTPUT_DIR}")
    logger.debug(f"  - MAX_FINAL_REPORTS: {config.MAX_FINAL_REPORTS}")
    logger.debug(f"  - OPENROUTER_API_KEY set: {bool(config.OPENROUTER_API_KEY)}")
except Exception as e:
    logger.error(f"❌ Failed to import config: {e}")
    traceback.print_exc()
    raise

try:
    from news_bot.discovery import search_client
    from news_bot.processing import article_handler
    from news_bot.generation import summarizer
    from news_bot.utils import file_manager, prompt_logger
    from news_bot.localization import translator
    logger.info("✅ News bot modules imported successfully")
except Exception as e:
    logger.error(f"❌ Failed to import news bot modules: {e}")
    traceback.print_exc()
    raise

logger.info("✅ All imports successful - creating Flask app...")

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'nexus-news-bot-secret-key')
logger.info("✅ Flask app created successfully")
logger.info(f"📦 App name: {app.name}")
logger.info(f"📁 Root path: {app.root_path}")

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
    'error': None,
    'start_time': None,
    'thread_id': None
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
    
    # Log progress update
    logger.info(f"[PROGRESS {progress}%] {message}")
    logger.debug(f"  -> Queue size before put: {progress_queue.qsize()}")
    logger.debug(f"  -> Status: found={current_job_status['articles_found']}, processed={current_job_status['articles_processed']}, generated={current_job_status['reports_generated']}")
    
    progress_queue.put(json.dumps(update))
    logger.debug(f"  -> Queue size after put: {progress_queue.qsize()}")

def run_news_bot_async(school_id, start_date_str, end_date_str, max_reports):
    """Run the news bot in a background thread."""
    global current_job_status
    
    thread_id = threading.current_thread().ident
    job_start_time = datetime.now()
    
    logger.info("=" * 60)
    logger.info(f"[JOB START] run_news_bot_async - Thread ID: {thread_id}")
    logger.info(f"[JOB START] Parameters: school_id={school_id}, start_date={start_date_str}, end_date={end_date_str}, max_reports={max_reports}")
    logger.info("=" * 60)
    
    try:
        current_job_status['running'] = True
        current_job_status['error'] = None
        current_job_status['progress'] = 0
        current_job_status['start_time'] = job_start_time.isoformat()
        current_job_status['thread_id'] = thread_id
        
        send_progress("🚀 Initializing Project NEXUS News Bot...", 5)
        
        # Validate configuration
        logger.info("[CONFIG] Validating configuration...")
        try:
            config.validate_config()
            logger.info("[CONFIG] Configuration validated successfully")
        except ValueError as e:
            logger.error(f"[CONFIG ERROR] Configuration validation failed: {e}")
            current_job_status['error'] = str(e)
            send_progress(f"❌ Configuration Error: {e}", 0)
            current_job_status['running'] = False
            return
        
        send_progress("✅ Configuration validated", 10)
        
        # Get selected school
        logger.info(f"[SCHOOL] Getting school with ID: {school_id}")
        schools_list = list(school_config.SCHOOL_PROFILES.values())
        logger.debug(f"[SCHOOL] Available schools: {[s['school_name'] for s in schools_list]}")
        
        if school_id < 1 or school_id > len(schools_list):
            error_msg = f"Invalid school_id: {school_id}. Valid range: 1-{len(schools_list)}"
            logger.error(f"[SCHOOL ERROR] {error_msg}")
            current_job_status['error'] = error_msg
            send_progress(f"❌ Error: {error_msg}", 0)
            current_job_status['running'] = False
            return
            
        chosen_school = schools_list[school_id - 1]
        logger.info(f"[SCHOOL] Selected school: {chosen_school['school_name']} (ID: {chosen_school['id']})")
        logger.debug(f"[SCHOOL] School config: {json.dumps({k: v for k, v in chosen_school.items() if k != 'prompt_context'}, default=str)}")
        
        send_progress(f"🎓 Selected: {chosen_school['school_name']}", 15)
        
        # Parse date range
        logger.info(f"[DATE] Parsing date range: start_date_str={start_date_str}, end_date_str={end_date_str}")
        if start_date_str and end_date_str:
            try:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
                logger.info(f"[DATE] Parsed dates: {start_date} to {end_date}")
            except ValueError as e:
                logger.error(f"[DATE ERROR] Failed to parse dates: {e}")
                current_job_status['error'] = f"Invalid date format: {e}"
                send_progress(f"❌ Error: Invalid date format", 0)
                current_job_status['running'] = False
                return
        else:
            start_date, end_date = config.get_news_date_range()
            logger.info(f"[DATE] Using default date range: {start_date} to {end_date}")
        
        days_span = (end_date - start_date).days + 1
        logger.info(f"[DATE] Date span: {days_span} days")
        
        send_progress(f"📅 Date range: {start_date} to {end_date}", 20)
        
        # Step 1: Discover articles
        send_progress("🔍 Discovering articles from news sources...", 25)
        logger.info("[DISCOVERY] Initializing prompt log...")
        prompt_log_file = prompt_logger.initialize_prompt_log()
        logger.info(f"[DISCOVERY] Prompt log file: {prompt_log_file}")
        
        # Temporarily override config date range for entire processing
        # This ensures discovery, verification, and all date checks use user-selected dates
        original_start_date = config.NEWS_START_DATE
        original_threshold = config.RECENCY_THRESHOLD_DAYS
        logger.info(f"[CONFIG OVERRIDE] Saving original config: NEWS_START_DATE={original_start_date}, RECENCY_THRESHOLD_DAYS={original_threshold}")
        
        try:
            # Override config with user-selected dates
            config.NEWS_START_DATE = start_date
            config.RECENCY_THRESHOLD_DAYS = days_span
            logger.info(f"[CONFIG OVERRIDE] Applied new config: NEWS_START_DATE={config.NEWS_START_DATE}, RECENCY_THRESHOLD_DAYS={config.RECENCY_THRESHOLD_DAYS}")
            
            logger.info("[DISCOVERY] Starting article discovery...")
            discovery_start_time = time.time()
            discovered_articles = search_client.find_relevant_articles(chosen_school)
            discovery_elapsed = time.time() - discovery_start_time
            logger.info(f"[DISCOVERY] Discovery completed in {discovery_elapsed:.2f}s")
        
            if not discovered_articles:
                logger.warning("[DISCOVERY] No articles discovered from any source")
                send_progress("ℹ️ No articles discovered. Job completed.", 100)
                current_job_status['running'] = False
                return
            
            logger.info(f"[DISCOVERY] Found {len(discovered_articles)} potential articles")
            for i, article in enumerate(discovered_articles[:5]):
                logger.debug(f"[DISCOVERY] Article {i+1}: {article.get('title', 'N/A')[:50]}... URL: {article.get('url', 'N/A')[:80]}...")
            if len(discovered_articles) > 5:
                logger.debug(f"[DISCOVERY] ... and {len(discovered_articles) - 5} more articles")
            
            current_job_status['articles_found'] = len(discovered_articles)
            send_progress(f"✅ Found {len(discovered_articles)} potential articles", 30)
            
            # Process articles
            final_news_reports = []
            processed_urls = set()
            articles_to_process = min(len(discovered_articles), max_reports)
            logger.info(f"[PROCESSING] Will process up to {articles_to_process} articles (max_reports={max_reports})")
            
            send_progress(f"⚙️ Processing articles (max: {max_reports})...", 35)
        
            for i, article_info in enumerate(discovered_articles):
                article_start_time = time.time()
                logger.info(f"[ARTICLE {i+1}/{len(discovered_articles)}] ========================================")
                
                if len(final_news_reports) >= max_reports:
                    logger.info(f"[ARTICLE {i+1}] Reached maximum number of reports ({max_reports}), stopping")
                    send_progress(f"✅ Reached maximum number of reports ({max_reports})", 90)
                    break
                
                progress = 35 + (50 * (i + 1) / articles_to_process)
                
                original_title = article_info.get("title", "N/A")
                article_url = article_info.get("url")
                source_method = article_info.get("source_method", "Unknown")
                article_date = article_info.get("url_date", "N/A")
                
                logger.info(f"[ARTICLE {i+1}] Title: {original_title[:70]}...")
                logger.info(f"[ARTICLE {i+1}] URL: {article_url}")
                logger.info(f"[ARTICLE {i+1}] Source: {source_method}, Date from URL: {article_date}")
                
                current_job_status['articles_processed'] = i + 1
                send_progress(f"📰 Processing: {original_title[:50]}...", progress)
                
                if not article_url or not article_url.startswith("http"):
                    logger.warning(f"[ARTICLE {i+1}] SKIP: Invalid or missing URL: {article_url}")
                    continue
                
                if article_url in processed_urls:
                    logger.warning(f"[ARTICLE {i+1}] SKIP: Already processed URL")
                    continue
                processed_urls.add(article_url)
                
                # Fetch and extract text
                logger.info(f"[ARTICLE {i+1}] Fetching and extracting text...")
                fetch_start = time.time()
                article_text = article_handler.fetch_and_extract_text(article_url)
                fetch_elapsed = time.time() - fetch_start
                
                if not article_text:
                    logger.warning(f"[ARTICLE {i+1}] SKIP: Failed to fetch/extract text (took {fetch_elapsed:.2f}s)")
                    continue
                logger.info(f"[ARTICLE {i+1}] Text extracted: {len(article_text)} chars, {len(article_text.split())} words (took {fetch_elapsed:.2f}s)")
                
                # Verify article
                logger.info(f"[ARTICLE {i+1}] Verifying article with AI...")
                verify_start = time.time()
                verification_results = article_handler.verify_article_with_gemini(
                    chosen_school, article_text, article_url, article_date
                )
                verify_elapsed = time.time() - verify_start
                
                if not verification_results:
                    logger.warning(f"[ARTICLE {i+1}] SKIP: Verification failed (took {verify_elapsed:.2f}s)")
                    continue
                
                logger.info(f"[ARTICLE {i+1}] Verification complete (took {verify_elapsed:.2f}s):")
                logger.info(f"[ARTICLE {i+1}]   - Date: {verification_results.get('publication_date_str')}")
                logger.info(f"[ARTICLE {i+1}]   - Is Recent: {verification_results.get('is_recent')}")
                logger.info(f"[ARTICLE {i+1}]   - Is Within Range: {verification_results.get('is_within_range')}")
                logger.info(f"[ARTICLE {i+1}]   - Is Relevant: {verification_results.get('is_relevant')}")
                logger.info(f"[ARTICLE {i+1}]   - Article Type: {verification_results.get('article_type_assessment')}")
                
                # Check if suitable for summary
                is_within_date_range = verification_results.get("is_within_range", False)
                if not is_within_date_range:
                    is_within_date_range = "Within range" in verification_results.get("is_recent", "") or "Recent" in verification_results.get("is_recent", "")
                
                allow_events = bool(chosen_school.get("include_event_announcements"))
                article_type = verification_results.get("article_type_assessment")
                allow_opinion = bool(chosen_school.get("include_opinion_blog"))
                
                logger.debug(f"[ARTICLE {i+1}] Suitability check: is_within_date_range={is_within_date_range}, allow_events={allow_events}, allow_opinion={allow_opinion}, article_type={article_type}")
                
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
                    logger.warning(f"[ARTICLE {i+1}] SKIP: Not suitable for summary - is_within_range={is_within_date_range}, is_relevant={verification_results.get('is_relevant')}, article_type={article_type}")
                    continue
                
                logger.info(f"[ARTICLE {i+1}] Article is suitable for summary, proceeding...")
                send_progress(f"✍️ Generating summary for: {original_title[:40]}...", progress)
                
                # Generate English summary
                logger.info(f"[ARTICLE {i+1}] Generating English summary...")
                summary_start = time.time()
                english_summary = summarizer.generate_summary_with_gemini(
                    chosen_school, article_text, article_url, original_title
                )
                summary_elapsed = time.time() - summary_start
                
                if not english_summary or "failed" in english_summary.lower():
                    logger.warning(f"[ARTICLE {i+1}] SKIP: Summary generation failed (took {summary_elapsed:.2f}s)")
                    logger.debug(f"[ARTICLE {i+1}] Summary result: {english_summary[:200] if english_summary else 'None'}...")
                    continue
                logger.info(f"[ARTICLE {i+1}] English summary generated: {len(english_summary)} chars (took {summary_elapsed:.2f}s)")
                
                send_progress(f"🌏 Translating to Chinese...", progress)
                
                # Translate to Chinese
                logger.info(f"[ARTICLE {i+1}] Translating to Chinese...")
                translate_start = time.time()
                english_report_data = {
                    "summary": english_summary,
                    "source_url": article_url,
                    "reported_publication_date": verification_results.get("publication_date_str", "N/A"),
                    "original_title": original_title
                }
                translation_output = translator.translate_and_restyle_to_chinese(english_report_data)
                translate_elapsed = time.time() - translate_start
                
                chinese_title = "中文标题失败"
                refined_chinese_report = "翻译失败"
                
                if translation_output:
                    chinese_title = translation_output.get("chinese_title", chinese_title)
                    refined_chinese_report = translation_output.get("refined_chinese_news_report", refined_chinese_report)
                    logger.info(f"[ARTICLE {i+1}] Translation complete (took {translate_elapsed:.2f}s)")
                    logger.info(f"[ARTICLE {i+1}]   - Chinese title: {chinese_title[:50]}...")
                    logger.info(f"[ARTICLE {i+1}]   - Chinese report: {len(refined_chinese_report)} chars")
                else:
                    logger.warning(f"[ARTICLE {i+1}] Translation returned None (took {translate_elapsed:.2f}s)")
                
                article_elapsed = time.time() - article_start_time
                
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
                logger.info(f"[ARTICLE {i+1}] ✅ REPORT GENERATED #{len(final_news_reports)} (article processing took {article_elapsed:.2f}s total)")
        
            # Save reports
            logger.info("[SAVE] Saving news reports...")
            send_progress("💾 Saving news reports...", 85)
            
            if final_news_reports:
                output_filename_base = f"weekly_student_news_report_{start_date}_{end_date}"
                logger.info(f"[SAVE] Output filename base: {output_filename_base}")
                logger.info(f"[SAVE] Output directory: {config.DEFAULT_OUTPUT_DIR}")
                
                saved_filepath = file_manager.save_data_to_json(final_news_reports, output_filename_base)
                
                if saved_filepath:
                    logger.info(f"[SAVE] ✅ Successfully saved {len(final_news_reports)} reports to: {saved_filepath}")
                    send_progress(f"✅ Saved {len(final_news_reports)} reports to JSON", 95)
                else:
                    logger.error("[SAVE] ❌ Failed to save reports - save_data_to_json returned None")
            
            # Write footer to prompt log
            if prompt_log_file:
                try:
                    with open(prompt_log_file, 'a', encoding='utf-8') as f:
                        f.write("\n" + "=" * 80 + "\n")
                        f.write(f"Run completed: {datetime.now().isoformat()}\n")
                        f.write(f"Date Range: {start_date} to {end_date}\n")
                        f.write(f"Total Reports: {len(final_news_reports)}\n")
                        f.write("=" * 80 + "\n")
                    logger.info(f"[PROMPT LOG] Footer written to: {prompt_log_file}")
                except Exception as e:
                    logger.warning(f"[PROMPT LOG] Failed to write footer: {e}")
            
            job_elapsed = datetime.now() - job_start_time
            logger.info("=" * 60)
            logger.info(f"[JOB COMPLETE] Generated {len(final_news_reports)} news reports")
            logger.info(f"[JOB COMPLETE] Total job duration: {job_elapsed}")
            logger.info("=" * 60)
            
            # Send completion message BEFORE setting running=False
            # This ensures the SSE stream gets the message before detecting job end
            if final_news_reports:
                send_progress(f"🎉 Complete! Generated {len(final_news_reports)} news reports", 100)
            else:
                send_progress("ℹ️ No suitable articles found for reporting", 100)
            
            # Give SSE time to process the message
            time.sleep(0.5)
        
        finally:
            # Restore original config after all processing is complete
            logger.info(f"[CONFIG RESTORE] Restoring original config: NEWS_START_DATE={original_start_date}, RECENCY_THRESHOLD_DAYS={original_threshold}")
            config.NEWS_START_DATE = original_start_date
            config.RECENCY_THRESHOLD_DAYS = original_threshold
        
    except Exception as e:
        logger.error(f"[JOB ERROR] Exception in run_news_bot_async: {e}")
        logger.error(f"[JOB ERROR] Traceback:\n{traceback.format_exc()}")
        current_job_status['error'] = str(e)
        send_progress(f"❌ Error: {e}", current_job_status['progress'])
        # Give SSE time to process the error message
        time.sleep(0.5)
    finally:
        job_end_time = datetime.now()
        job_duration = job_end_time - job_start_time
        logger.info(f"[JOB END] run_news_bot_async finished. Duration: {job_duration}")
        logger.info(f"[JOB END] Final status before setting running=False: running={current_job_status['running']}, error={current_job_status['error']}")
        logger.info(f"[JOB END] Reports generated: {current_job_status['reports_generated']}")
        current_job_status['running'] = False
        logger.info(f"[JOB END] Set running=False")

@app.route('/')
def index():
    """Render the main page."""
    logger.info("[ROUTE /] Index page requested")
    try:
        # Ensure output directory exists (lazy initialization)
        os.makedirs(config.DEFAULT_OUTPUT_DIR, exist_ok=True)
        logger.debug(f"[ROUTE /] Output directory ensured: {config.DEFAULT_OUTPUT_DIR}")
        
        schools = school_config.SCHOOL_PROFILES
        start_date, end_date = config.get_news_date_range()
        
        logger.info(f"[ROUTE /] Rendering index with {len(schools)} schools, date range: {start_date} to {end_date}")
        
        return render_template('index.html', 
                             schools=schools,
                             default_start_date=start_date.isoformat(),
                             default_end_date=end_date.isoformat(),
                             max_reports=config.MAX_FINAL_REPORTS)
    except Exception as e:
        # Graceful fallback if config fails
        logger.error(f"[ROUTE /] Error loading index: {e}")
        logger.error(traceback.format_exc())
        
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
    
    logger.info("[API /api/start] Received start job request")
    
    if current_job_status['running']:
        logger.warning("[API /api/start] Job already running, rejecting request")
        return jsonify({'error': 'A job is already running'}), 400
    
    data = request.json
    logger.info(f"[API /api/start] Request data: {data}")
    
    school_id = data.get('school_id', 1)
    start_date = data.get('start_date', None)
    end_date = data.get('end_date', None)
    max_reports = data.get('max_reports', config.MAX_FINAL_REPORTS)
    
    logger.info(f"[API /api/start] Parsed parameters: school_id={school_id}, start_date={start_date}, end_date={end_date}, max_reports={max_reports}")
    
    # Reset status
    current_job_status = {
        'running': True,
        'progress': 0,
        'current_step': 'Starting...',
        'articles_found': 0,
        'articles_processed': 0,
        'reports_generated': 0,
        'error': None,
        'start_time': datetime.now().isoformat(),
        'thread_id': None
    }
    logger.info(f"[API /api/start] Reset job status: {current_job_status}")
    
    # Clear the queue
    queue_size_before = progress_queue.qsize()
    while not progress_queue.empty():
        try:
            progress_queue.get_nowait()
        except:
            break
    logger.info(f"[API /api/start] Cleared progress queue (was {queue_size_before} items)")
    
    # Start background thread
    logger.info("[API /api/start] Starting background thread...")
    thread = threading.Thread(
        target=run_news_bot_async,
        args=(school_id, start_date, end_date, max_reports)
    )
    thread.daemon = True
    thread.start()
    logger.info(f"[API /api/start] Background thread started: {thread.name} (ident: {thread.ident})")
    
    return jsonify({'message': 'Job started successfully', 'thread_id': thread.ident})

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get current job status."""
    logger.debug(f"[API /api/status] Returning status: running={current_job_status['running']}, progress={current_job_status['progress']}")
    return jsonify(current_job_status)

@app.route('/api/debug', methods=['GET'])
def get_debug_info():
    """Get detailed debug information."""
    logger.info("[API /api/debug] Debug info requested")
    
    debug_info = {
        'timestamp': datetime.now().isoformat(),
        'job_status': current_job_status.copy(),
        'queue_size': progress_queue.qsize(),
        'config': {
            'DEFAULT_OUTPUT_DIR': config.DEFAULT_OUTPUT_DIR,
            'MAX_FINAL_REPORTS': config.MAX_FINAL_REPORTS,
            'MAX_SEARCH_RESULTS_TO_PROCESS': config.MAX_SEARCH_RESULTS_TO_PROCESS,
            'OPENROUTER_API_KEY_SET': bool(config.OPENROUTER_API_KEY),
            'GEMINI_PRO_MODEL': config.GEMINI_PRO_MODEL,
        },
        'date_range': {
            'start': config.get_news_date_range()[0].isoformat(),
            'end': config.get_news_date_range()[1].isoformat(),
            'NEWS_START_DATE': str(config.NEWS_START_DATE),
            'RECENCY_THRESHOLD_DAYS': config.RECENCY_THRESHOLD_DAYS,
        },
        'schools': [
            {'id': info['id'], 'name': info['school_name']}
            for info in school_config.SCHOOL_PROFILES.values()
        ],
        'output_dir_exists': os.path.exists(config.DEFAULT_OUTPUT_DIR),
        'output_dir_files': len(os.listdir(config.DEFAULT_OUTPUT_DIR)) if os.path.exists(config.DEFAULT_OUTPUT_DIR) else 0,
        'active_threads': threading.active_count(),
    }
    
    logger.debug(f"[API /api/debug] Debug info: {json.dumps(debug_info, default=str)}")
    return jsonify(debug_info)

@app.route('/api/progress')
def progress_stream():
    """Server-Sent Events endpoint for real-time progress updates."""
    logger.info("[API /api/progress] SSE connection opened")
    
    def generate():
        from queue import Empty
        connection_start = time.time()
        message_count = 0
        heartbeat_count = 0
        last_progress = -1
        
        try:
            while True:
                # Use timeout to allow checking if connection should close
                try:
                    message = progress_queue.get(timeout=10)
                    message_count += 1
                    
                    # Parse message to check progress
                    try:
                        msg_data = json.loads(message)
                        current_progress = msg_data.get('progress', 0)
                        if current_progress != last_progress:
                            logger.info(f"[SSE] Progress update: {current_progress}% - {msg_data.get('message', 'N/A')[:50]}...")
                            last_progress = current_progress
                    except:
                        pass
                    
                    logger.debug(f"[SSE] Sending message #{message_count}")
                    yield f"data: {message}\n\n"
                    
                    # Check if job is complete after sending message
                    if last_progress >= 100:
                        logger.info(f"[SSE] Job complete (100%), will close after queue empties")
                        # Drain remaining queue
                        while not progress_queue.empty():
                            try:
                                remaining = progress_queue.get_nowait()
                                yield f"data: {remaining}\n\n"
                            except Empty:
                                break
                        break
                        
                except Empty:
                    # Timeout - send heartbeat or check if should close
                    if not current_job_status['running'] and progress_queue.empty():
                        logger.info(f"[SSE] Job finished and queue empty, closing connection after {message_count} messages")
                        # Send final status
                        final_status = json.dumps({
                            'type': 'complete',
                            'message': 'Job finished',
                            'progress': current_job_status['progress'],
                            'reports_generated': current_job_status['reports_generated'],
                            'timestamp': datetime.now().isoformat()
                        })
                        yield f"data: {final_status}\n\n"
                        break
                    
                    # Send heartbeat to keep connection alive
                    heartbeat_count += 1
                    heartbeat = json.dumps({
                        'type': 'heartbeat',
                        'timestamp': datetime.now().isoformat(),
                        'queue_size': progress_queue.qsize(),
                        'running': current_job_status['running'],
                        'progress': current_job_status['progress']
                    })
                    if heartbeat_count % 6 == 0:  # Log every minute (6 * 10s)
                        logger.debug(f"[SSE] Heartbeat #{heartbeat_count}: running={current_job_status['running']}, progress={current_job_status['progress']}")
                    yield f"data: {heartbeat}\n\n"
                    
        except GeneratorExit:
            connection_duration = time.time() - connection_start
            logger.info(f"[SSE] Connection closed by client after {connection_duration:.1f}s, {message_count} messages sent")
        except Exception as e:
            logger.error(f"[SSE] Error in generate: {e}")
            import traceback
            logger.error(f"[SSE] Traceback: {traceback.format_exc()}")
            raise
    
    return Response(generate(), mimetype='text/event-stream', headers={
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'X-Accel-Buffering': 'no'
    })

@app.route('/api/reports', methods=['GET'])
def list_reports():
    """List all generated reports."""
    logger.info("[API /api/reports] Listing all reports")
    try:
        # Ensure output directory exists
        os.makedirs(config.DEFAULT_OUTPUT_DIR, exist_ok=True)
        reports_dir = config.DEFAULT_OUTPUT_DIR
        logger.debug(f"[API /api/reports] Reports directory: {reports_dir}")
        
        if not os.path.exists(reports_dir):
            logger.warning(f"[API /api/reports] Reports directory does not exist")
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
        logger.info(f"[API /api/reports] Found {len(reports)} reports")
        if reports:
            logger.debug(f"[API /api/reports] Most recent: {reports[0]['filename']}")
        return jsonify({'reports': reports})
    except Exception as e:
        logger.error(f"[API /api/reports] Error listing reports: {e}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e), 'reports': []}), 500

@app.route('/api/reports/<filename>', methods=['GET'])
def get_report(filename):
    """Get a specific report."""
    logger.info(f"[API /api/reports/<filename>] Fetching report: {filename}")
    try:
        # Sanitize filename to prevent directory traversal
        original_filename = filename
        filename = os.path.basename(filename)
        if original_filename != filename:
            logger.warning(f"[API /api/reports/<filename>] Filename sanitized: {original_filename} -> {filename}")
        
        filepath = os.path.join(config.DEFAULT_OUTPUT_DIR, filename)
        logger.debug(f"[API /api/reports/<filename>] Full path: {filepath}")
        
        if not os.path.exists(filepath):
            logger.warning(f"[API /api/reports/<filename>] Report not found: {filepath}")
            return jsonify({'error': 'Report not found'}), 404
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        logger.info(f"[API /api/reports/<filename>] Successfully loaded report with {len(data) if isinstance(data, list) else 'N/A'} items")
        return jsonify(data)
    except json.JSONDecodeError as e:
        logger.error(f"[API /api/reports/<filename>] JSON decode error: {e}")
        return jsonify({'error': f'Invalid JSON in report file: {e}'}), 500
    except Exception as e:
        logger.error(f"[API /api/reports/<filename>] Error: {e}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/save-report', methods=['POST'])
def save_report():
    """Save edited report data back to JSON file."""
    logger.info("[API /api/save-report] Saving edited report")
    data = request.json
    report_filename = data.get('report_filename')
    report_data = data.get('report_data')
    
    logger.debug(f"[API /api/save-report] Filename: {report_filename}")
    logger.debug(f"[API /api/save-report] Data items: {len(report_data) if isinstance(report_data, list) else 'N/A'}")
    
    if not report_filename or not report_data:
        logger.warning("[API /api/save-report] Missing filename or data")
        return jsonify({'error': 'Report filename and data are required'}), 400
    
    report_path = Path(config.DEFAULT_OUTPUT_DIR) / report_filename
    logger.info(f"[API /api/save-report] Saving to: {report_path}")
    
    try:
        # Save the edited data
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"[API /api/save-report] ✅ Report saved successfully")
        return jsonify({
            'success': True,
            'message': 'Report saved successfully'
        })
    except Exception as e:
        logger.error(f"[API /api/save-report] Error saving report: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'error': 'Failed to save report',
            'details': str(e)
        }), 500

@app.route('/api/ai-edit', methods=['POST'])
def ai_edit_text():
    """Use AI to edit text based on user prompt."""
    logger.info("[API /api/ai-edit] AI edit request received")
    data = request.json
    text = data.get('text', '')
    prompt = data.get('prompt', '')
    article_index = data.get('article_index', None)
    
    logger.debug(f"[API /api/ai-edit] Article index: {article_index}")
    logger.debug(f"[API /api/ai-edit] Text length: {len(text)}")
    logger.debug(f"[API /api/ai-edit] User prompt: {prompt[:100]}...")
    
    if not text or not prompt:
        logger.warning("[API /api/ai-edit] Missing text or prompt")
        return jsonify({'error': 'Text and prompt are required'}), 400
    
    try:
        from news_bot.utils.openrouter_client import generate_content
        
        # Create a comprehensive prompt for editing
        edit_prompt = f"""You are a professional Chinese news editor. The user wants you to edit the following Chinese news text.

User's request: {prompt}

Original text:
{text}

Please provide ONLY the edited text, without any explanations or additional comments. Return the complete edited text that addresses the user's request."""
        
        logger.info("[API /api/ai-edit] Sending request to OpenRouter...")
        edit_start = time.time()
        edited_text = generate_content(edit_prompt, temperature=0.7)
        edit_elapsed = time.time() - edit_start
        
        if not edited_text:
            logger.error(f"[API /api/ai-edit] OpenRouter returned no content (took {edit_elapsed:.2f}s)")
            return jsonify({
                'error': 'Failed to get AI response',
                'details': 'OpenRouter API returned no content'
            }), 500
        
        logger.info(f"[API /api/ai-edit] ✅ AI edit successful (took {edit_elapsed:.2f}s)")
        logger.debug(f"[API /api/ai-edit] Result length: {len(edited_text)}")
        
        return jsonify({
            'success': True,
            'edited_text': edited_text.strip()
        })
        
    except Exception as e:
        logger.error(f"[API /api/ai-edit] Error: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'error': 'Failed to edit text with AI',
            'details': str(e)
        }), 500

@app.route('/api/generate-images', methods=['POST'])
def generate_wechat_images():
    """Generate WeChat-style images directly from JSON report (no Google Docs needed)."""
    logger.info("[API /api/generate-images] Image generation request received")
    data = request.json
    report_filename = data.get('report_filename')
    report_data = data.get('report_data')  # Optional: use edited data instead of file
    
    logger.debug(f"[API /api/generate-images] Filename: {report_filename}")
    logger.debug(f"[API /api/generate-images] Has report_data: {report_data is not None}")
    
    if not report_filename:
        logger.warning("[API /api/generate-images] Missing report filename")
        return jsonify({'error': 'Report filename is required'}), 400
    
    report_path = Path(config.DEFAULT_OUTPUT_DIR) / report_filename
    logger.debug(f"[API /api/generate-images] Report path: {report_path}")
    
    # If edited data provided, save it temporarily
    if report_data:
        logger.info("[API /api/generate-images] Using provided report_data (not file)")
        temp_path = Path(tempfile.mkdtemp()) / report_filename
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        json_path = str(temp_path)
        logger.debug(f"[API /api/generate-images] Saved temp file: {json_path}")
    else:
        if not report_path.exists():
            logger.warning(f"[API /api/generate-images] Report file not found: {report_path}")
            return jsonify({'error': f'Report file not found: {report_filename}'}), 404
        json_path = str(report_path)
        logger.debug(f"[API /api/generate-images] Using existing file: {json_path}")
    
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
logger.info("=" * 60)
logger.info("✅ NEXUS Flask app fully loaded - ready for requests")
logger.info(f"📝 Total routes registered: {len(app.url_map._rules)}")
for rule in app.url_map.iter_rules():
    logger.debug(f"  Route: {rule.rule} -> {rule.endpoint} [{', '.join(rule.methods - {'HEAD', 'OPTIONS'})}]")
logger.info("=" * 60)

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

