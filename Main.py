# main.py

import requests
import re
import traceback
from config import API_URL, HEADERS, TODAY, DISPLAY_DATE

# Prompt template
prompt_template = (
    "You are a professional English-language news writer creating a daily briefing for Chinese international students at New York University (NYU).\n\n"
    "Your task is to produce exactly five independent news summaries, each based on a different genuine and reliable news source from and ONLY FROM the past seven days, up to and including {today}.\n\n"
    "Each summary should focus on a different news story relevant to Chinese students’ study, work, daily life, or immigration policy, especially in New York or the U.S.\n\n"
    "Write five distinct summaries labeled as 'Summary 1:', 'Summary 2:', etc.\n\n"
    "Each summary should be 200–400 words and describe what happened, when, where, who was involved, and what the consequences are.\n\n"
    "Use clear, objective language. Avoid speculation, emotional tone, rhetorical questions, or subjective opinions. Maintain a neutral and formal style suitable for university readers.\n\n"
    "At the end of each summary, include a 'Sources:' section with the actual URLs used. Each summary must be supported by at least one unique and valid source link.\n\n"
    "Do not include any in-text citations (e.g., [1], [2]), and do not refer to source names in the main body.\n\n"
    "Do NOT mention search result numbers like 'Result [14]' or refer to Perplexity or search formatting.\n\n"
    "If limited news is available, explain that explicitly within the affected summary, but still make sure all five summaries cover different topics from different sources."
).replace("{today}", TODAY)

# Build request
payload = {
    "model": "sonar-deep-research",
    "messages": [
        {
            "role": "system",
            "content": (
                "You are a professional English-language news writer generating neutral, factual summaries. Each summary must be about a unique news event "
                "with a different source, using only real and recent stories from the past seven days. Do NOT include any bracketed numbers like '[1]', '[2]', etc."
            )
        },
        {
            "role": "user",
            "content": prompt_template
        }
    ],
    "temperature": 0.1,
    "max_tokens": 4000
}

# Execute API request
try:
    print("Sending request to Perplexity API...")
    response = requests.post(API_URL, headers=HEADERS, json=payload, timeout=600)
    response.raise_for_status()
    result = response.json()
    print("Response received.")

    content = result["choices"][0]["message"]["content"].strip()
    content = re.sub(r"\[\d+\]", "", content)

    summaries = re.findall(r"Summary\s*([1-5]):\s*(.+?)(?=Summary\s*[1-5]:|$)", content, re.S)

    for num, body in summaries:
        filename = f"NYU_Summary_{num}_{TODAY}.md"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"Summary {num} – NYU Weekly Report ({DISPLAY_DATE})\n\n")
            f.write(body.strip() + "\n")
        print(f"Saved file: {filename}")

except Exception:
    print("An error occurred:")
    print(traceback.format_exc())
