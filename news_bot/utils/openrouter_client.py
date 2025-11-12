# news_bot/utils/openrouter_client.py

import requests
from ..core import config


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
        print("Error: OPENROUTER_API_KEY not configured.")
        return None
    
    if model is None:
        model = config.GEMINI_PRO_MODEL
    
    headers = {
        "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/your-repo",  # Optional: for OpenRouter tracking
        "X-Title": "NEXUS News Bot"  # Optional: for OpenRouter tracking
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
    
    try:
        response = requests.post(
            config.OPENROUTER_API_URL,
            headers=headers,
            json=payload,
            timeout=60
        )
        response.raise_for_status()
        
        data = response.json()
        
        # Extract content from OpenRouter response
        if "choices" in data and len(data["choices"]) > 0:
            content = data["choices"][0].get("message", {}).get("content", "").strip()
            return content
        
        print(f"Error: Unexpected response format from OpenRouter: {data}")
        return None
        
    except requests.exceptions.RequestException as e:
        print(f"Error during OpenRouter API call: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_data = e.response.json()
                print(f"Error details: {error_data}")
            except:
                print(f"Error response: {e.response.text}")
        return None
    except Exception as e:
        print(f"Unexpected error during OpenRouter API call: {e}")
        return None

