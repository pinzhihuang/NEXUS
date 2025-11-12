# news_bot/utils/prompt_logger.py

import os
from datetime import datetime
from threading import Lock
from ..core import config

# Global state for prompt logging
_prompt_log_file = None
_prompt_log_lock = Lock()
_prompt_counter = 0

def initialize_prompt_log():
    """Initialize the prompt log file at the start of a run."""
    global _prompt_log_file, _prompt_counter
    
    with _prompt_log_lock:
        if _prompt_log_file is not None:
            return _prompt_log_file
        
        # Create logs directory if it doesn't exist
        logs_dir = os.path.join(config.PROJECT_ROOT, "prompt_logs")
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir)
        
        # Create timestamped log file
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        log_filename = f"gemini_prompts_{timestamp}.txt"
        log_filepath = os.path.join(logs_dir, log_filename)
        
        _prompt_log_file = log_filepath
        _prompt_counter = 0
        
        # Write header to log file
        with open(log_filepath, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write(f"Gemini API Prompts Log\n")
            f.write(f"Run started: {datetime.now().isoformat()}\n")
            f.write("=" * 80 + "\n\n")
        
        print(f"Prompt logging initialized: {log_filepath}")
        return log_filepath

def log_prompt(function_name: str, prompt: str, context: dict = None):
    """
    Log a prompt sent to Gemini API.
    
    Args:
        function_name: Name of the function making the API call
        prompt: The prompt text sent to Gemini
        context: Optional dictionary with additional context (e.g., article_url, article_title)
    """
    global _prompt_log_file, _prompt_counter
    
    with _prompt_log_lock:
        # Initialize log file if not already done
        if _prompt_log_file is None:
            initialize_prompt_log()
        
        _prompt_counter += 1
        
        try:
            with open(_prompt_log_file, 'a', encoding='utf-8') as f:
                f.write(f"\n{'=' * 80}\n")
                f.write(f"Prompt #{_prompt_counter} - {function_name}\n")
                f.write(f"Timestamp: {datetime.now().isoformat()}\n")
                
                if context:
                    f.write(f"\nContext:\n")
                    for key, value in context.items():
                        # Truncate long values for readability
                        if isinstance(value, str) and len(value) > 200:
                            f.write(f"  {key}: {value[:200]}... (truncated, full length: {len(value)})\n")
                        else:
                            f.write(f"  {key}: {value}\n")
                
                f.write(f"\nPrompt:\n")
                f.write("-" * 80 + "\n")
                f.write(prompt)
                f.write("\n" + "-" * 80 + "\n")
                f.write(f"\n")
        except Exception as e:
            print(f"Warning: Failed to log prompt: {e}")

def get_prompt_log_file():
    """Get the current prompt log file path."""
    return _prompt_log_file

def get_prompt_count():
    """Get the current prompt count."""
    return _prompt_counter

def reset_prompt_log():
    """Reset the prompt log (for testing or new runs)."""
    global _prompt_log_file, _prompt_counter
    with _prompt_log_lock:
        _prompt_log_file = None
        _prompt_counter = 0

