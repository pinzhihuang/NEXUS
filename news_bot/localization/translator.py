# news_bot/localization/translator.py

from ..core import config
from ..utils import prompt_logger, openrouter_client
# import re # Not strictly needed if not doing complex regex here

# Note: Refinement is now combined with translation in translate_and_restyle_to_chinese()
# This function is kept for backward compatibility but is no longer used
def _refine_chinese_news_report_with_gemini(chinese_text: str, source_url: str, publication_date: str, original_title: str) -> str:
    """
    DEPRECATED: Refinement is now done as part of translation.
    This function is kept for backward compatibility.
    """
    return chinese_text

def translate_and_restyle_to_chinese(english_summary_data: dict) -> dict | None:
    """
    Translates English summary to Chinese, generates title, and refines the report in ONE comprehensive step.
    Uses Gemini 2.5 Pro for better quality and accuracy.
    Combines translation + refinement to reduce LLM calls.
    """
    if not config.OPENROUTER_API_KEY:
        print("Error: OPENROUTER_API_KEY not configured for translation.")
        return None

    english_summary = english_summary_data.get('summary', '')
    source_url = english_summary_data.get('source_url', 'Unknown source')
    publication_date = english_summary_data.get('reported_publication_date', 'Date not available')
    original_title = english_summary_data.get('original_title', 'N/A')

    default_error_return = {
        "chinese_title": "标题生成失败 (Title generation failed)",
        "refined_chinese_news_report": "翻译失败或跳过 (Translation failed or skipped)"
    }

    if not english_summary.strip():
        print(f"Info: Skipping translation for {source_url} due to empty English summary.")
        return {
            "chinese_title": "无标题 (No title for empty summary)",
            "refined_chinese_news_report": "翻译跳过：英文摘要为空 (Translation skipped: English summary was empty)"
        }

    print(f"Translating, generating title, and refining Chinese news report for: {source_url[:100]}...")

    prompt = f"""你是一位专业的中文新闻写作者和翻译。你的任务是将英文新闻摘要翻译成一篇准确、精炼的中文新闻，并生成一个吸引人的标题。

## 角色
你是一位专业的中文新闻写作者，专门为中国留学生撰写准确、精炼的新闻。

## 任务
将英文新闻摘要翻译成简体中文，生成一个吸引人的标题，并在一步中完成翻译和精炼。

## 要求

### 准确性与事实性（最高优先级）
- 仅翻译英文摘要中明确陈述的信息 - 不要添加、推断或猜测
- 保留所有事实细节：日期、姓名、数字、地点、组织
- 不要添加原文中没有的后果、影响或观点
- 避免使用"可能"、"引发"、"导致"等暗示未陈述后果的词语
- 对照原始英文文本验证所有翻译

### 标题生成要求
1. 创建简洁、相关且吸引人的简体中文新闻标题
2. 将标题放在第一行，前缀为"Chinese Title:"
3. 如果单行标题超过15个中文字符，将其分成2个逗号分隔的段落，每段≤12个字符，在自然语义断点处分割
4. 每个段落必须形成一个完整的短语（例如：主谓或动宾），不能是孤立的名词
5. 对于每条新闻，考虑三种标题风格：
   a) 弱点击诱式
   b) 口语化风格
   c) 简洁直接
   选择最适合新闻主题的风格
6. 避免使用隐喻、成语、谚语、双关语、谐音或其他修辞手法
7. 避免过于正式或文学化的措辞 - 使用直接、自然的用词
8. 避免单字缩写（例如：不要用"美"来代指"全美"）

### 翻译与内容要求
1. 将英文摘要翻译成简体中文新闻文章格式
2. 如果英文摘要包含多个新闻主题，选择最重要的一个并专注于它 - 保持文章连贯
3. 不要试图包含原始英文摘要中的所有信息 - 优先考虑关键事实
4. 对于不太常见的英文人名、组织名或项目名，翻译成中文并在括号中保留英文：中文名 (English Name)
5. 对于非常知名的实体或常见的英文名称，可以直接使用中文翻译

### 风格与精炼要求
1. 使用严肃、正式、客观的新闻写作风格
2. 使用短句和准确的词汇 - 避免复杂的长句
3. 保持语言自然专业 - 尽量减少形容词
4. 保持句子之间的逻辑连贯有序
5. 不要包含额外的评论或观点
6. 不要写结论 - 如果提到，可以以最新更新结尾，例如："目前，学校对此事件还没有做出回应。"

### 结构与格式要求
1. 每个关键事实点必须包含至少2句话：
   - 第一句：核心事实的主要描述
   - 第二句：阐述背景，提供具体细节、解释、影响、后续事件、采访引语（如有）或背景信息
2. 如果两个相似或相关的事实存在，将它们合并为一个段落，而不是分开的段落
3. 控制每个段落为80-250个中文字符 - 超过此长度的段落必须在保持逻辑连贯性的情况下分割，段落之间要有明确的因果或时间关系
4. 总长度：250-500个中文字符
5. 特别注意最后一句话 - 确保它切题并具有价值
6. 删除任何对核心新闻故事没有事实价值的句子或短语

## 输入数据

原始英文摘要（用于翻译）：
'''
{english_summary}
'''
原始文章标题（供参考）：{original_title}

## 输出格式

你的回复必须严格按照以下格式：
- 第1行："Chinese Title: [你的中文标题]"
- 第2行：（空行）
- 第3行及以后：[精炼的中文新闻正文]

"Chinese Title:"之后的内容应该只是精炼的中文新闻正文 - 不要添加任何评论。

你的回复：
"""
    chinese_title = default_error_return["chinese_title"]
    refined_chinese_report = default_error_return["refined_chinese_news_report"]

    try:
        print(f"Sending translation+refinement request to OpenRouter API ({config.GEMINI_PRO_MODEL})...")
        
        # Log the prompt
        prompt_logger.log_prompt(
            "translate_and_restyle_to_chinese",
            prompt,
            context={
                "source_url": source_url,
                "publication_date": publication_date,
                "original_title": original_title,
                "english_summary_length": len(english_summary)
            }
        )
        
        full_response_text = openrouter_client.generate_content(
            prompt=prompt,
            model=config.GEMINI_PRO_MODEL,
            temperature=0.7
        )
        
        if full_response_text:
            # Parse the response - look for "Chinese Title:" prefix
            lines = full_response_text.split('\n')
            title_line_idx = None
            for i, line in enumerate(lines):
                if line.strip().startswith("Chinese Title:"):
                    title_line_idx = i
                    break
            
            if title_line_idx is not None:
                # Extract title
                title_line = lines[title_line_idx].replace("Chinese Title:", "").strip()
                chinese_title = title_line
                
                # Extract report body (everything after title line, skipping blank lines)
                report_lines = []
                for i in range(title_line_idx + 1, len(lines)):
                    line = lines[i].strip()
                    if line:  # Skip blank lines
                        report_lines.append(line)
                
                if report_lines:
                    refined_chinese_report = '\n'.join(report_lines)
                else:
                    print(f"Warning: OpenRouter response had title but no report body for {source_url}.")
                    refined_chinese_report = default_error_return["refined_chinese_news_report"]
            else:
                # No title prefix found - try to extract from first line or use entire response
                print(f"Warning: OpenRouter response did not start with 'Chinese Title:' for {source_url}. Attempting to parse...")
                if lines:
                    # Try to use first line as title if it looks like a title
                    first_line = lines[0].strip()
                    if len(first_line) <= 30 and not first_line.endswith('。'):
                        chinese_title = first_line
                        refined_chinese_report = '\n'.join(lines[1:]).strip() if len(lines) > 1 else default_error_return["refined_chinese_news_report"]
                    else:
                        # Entire response is report, generate default title
                        refined_chinese_report = full_response_text
                else:
                    refined_chinese_report = default_error_return["refined_chinese_news_report"]
        else:
            print(f"Warning: Empty response from OpenRouter for translation+refinement of {source_url}.")
            # Errors already set in defaults

    except Exception as e:
        print(f"Error during OpenRouter API call for translation+refinement of {source_url}: {e}")
        # Errors already set in defaults

    # Ensure some content exists, even if it's an error placeholder
    if not chinese_title.strip(): 
        chinese_title = default_error_return["chinese_title"]
    if not refined_chinese_report.strip(): 
        refined_chinese_report = default_error_return["refined_chinese_news_report"]

    print(f"Translation+refinement complete for {source_url[:100]}... Title: '{chinese_title[:50]}...'")

    # Return refined Chinese report (translation and refinement are now combined in one step)
    return {
        "chinese_title": chinese_title,
        "refined_chinese_news_report": refined_chinese_report
    }

if __name__ == '__main__':
    print("Testing Translator Module (with Refinement)...")
    import sys
    import os
    PROJECT_ROOT_FOR_TEST = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if PROJECT_ROOT_FOR_TEST not in sys.path:
         sys.path.insert(0, PROJECT_ROOT_FOR_TEST)
    
    from news_bot.core import config 
    config.validate_config()
    if not hasattr(config, 'GEMINI_FLASH_MODEL_CONTEXT_LIMIT_CHARS'):
        config.GEMINI_FLASH_MODEL_CONTEXT_LIMIT_CHARS = 100000

    sample_english_data = {
        "summary": "NYU announced a new visa support initiative. This helps international students, especially those from China, facing visa delays. President Linda G. Mills stated NYU is committed. Workshops and extended advising are included. Hundreds will benefit next academic year.",
        "source_url": "https://www.nyu.edu/news/2024/05/21/visa-support-initiative.html",
        "reported_publication_date": "2024-05-21",
        "original_title": "NYU Launches New Visa Support Initiative for International Students"
    }

    print(f"\n--- Test Translation, Title & Refinement for: {sample_english_data['source_url']} ---")
    translation_output = translate_and_restyle_to_chinese(sample_english_data)

    if translation_output:
        print(f"\nGenerated Chinese Title: {translation_output.get('chinese_title')}")
        print(f"\nChinese News Report:\n{translation_output.get('refined_chinese_news_report')}")
    else:
        print("\nFailed to generate Chinese news report and title (None returned).") 