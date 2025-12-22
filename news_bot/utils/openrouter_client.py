# news_bot/utils/openrouter_client.py

import requests
import logging
import time
from ..core import config

# Setup logging
logger = logging.getLogger('openrouter_client')


def generate_content(prompt: str, model: str = None, temperature: float = 0.7) -> str | None:
    """
    Generate content using OpenRouter API.
    
    Args:
        prompt: The prompt text to send to the model
        model: Model name (defaults to GEMINI_PRO_MODEL from config)
        temperature: Temperature for generation (default 0.7)
    
    Returns:
        Generated text content or None if error
    """
    if not config.OPENROUTER_API_KEY:
        logger.error("[OPENROUTER] OPENROUTER_API_KEY not configured")
        print("Error: OPENROUTER_API_KEY not configured.")
        return None
    
    if model is None:
        model = config.GEMINI_PRO_MODEL
    
    logger.info(f"[OPENROUTER] Generating content with model: {model}")
    logger.debug(f"[OPENROUTER] Prompt length: {len(prompt)} chars")
    logger.debug(f"[OPENROUTER] Temperature: {temperature}")
    
    headers = {
        "Authorization": f"Bearer {config.OPENROUTER_API_KEY[:10]}...",  # Masked for logging
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/your-repo",  # Optional: for OpenRouter tracking
        "X-Title": "NEXUS News Bot"  # Optional: for OpenRouter tracking
    }
    
    # Actual headers with full API key
    actual_headers = {
        "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/your-repo",
        "X-Title": "NEXUS News Bot"
    }
    
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": temperature
    }
    
    start_time = time.time()
    try:
        logger.debug(f"[OPENROUTER] Sending request to {config.OPENROUTER_API_URL}")
        response = requests.post(
            config.OPENROUTER_API_URL,
            headers=actual_headers,
            json=payload,
            timeout=120  # Increased timeout for longer responses
        )
        elapsed = time.time() - start_time
        logger.info(f"[OPENROUTER] Response received in {elapsed:.2f}s, status: {response.status_code}")
        
        response.raise_for_status()
        
        data = response.json()
        
        # Extract content from OpenRouter response
        if "choices" in data and len(data["choices"]) > 0:
            content = data["choices"][0].get("message", {}).get("content", "").strip()
            logger.info(f"[OPENROUTER] ✅ Content generated: {len(content)} chars")
            logger.debug(f"[OPENROUTER] Response preview: {content[:200]}...")
            
            # Log usage info if available
            if "usage" in data:
                usage = data["usage"]
                logger.debug(f"[OPENROUTER] Tokens - prompt: {usage.get('prompt_tokens', 'N/A')}, completion: {usage.get('completion_tokens', 'N/A')}, total: {usage.get('total_tokens', 'N/A')}")
            
            return content
        
        logger.error(f"[OPENROUTER] Unexpected response format: {data}")
        print(f"Error: Unexpected response format from OpenRouter: {data}")
        return None
        
    except requests.exceptions.Timeout as e:
        elapsed = time.time() - start_time
        logger.error(f"[OPENROUTER] Timeout after {elapsed:.2f}s: {e}")
        print(f"Error: OpenRouter API timeout: {e}")
        return None
    except requests.exceptions.RequestException as e:
        elapsed = time.time() - start_time
        logger.error(f"[OPENROUTER] Request error after {elapsed:.2f}s: {e}")
        print(f"Error during OpenRouter API call: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_data = e.response.json()
                logger.error(f"[OPENROUTER] Error details: {error_data}")
                print(f"Error details: {error_data}")
            except:
                logger.error(f"[OPENROUTER] Error response text: {e.response.text[:500]}")
                print(f"Error response: {e.response.text}")
        return None
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"[OPENROUTER] Unexpected error after {elapsed:.2f}s: {e}")
        import traceback
        logger.error(f"[OPENROUTER] Traceback: {traceback.format_exc()}")
        print(f"Unexpected error during OpenRouter API call: {e}")
        return None

