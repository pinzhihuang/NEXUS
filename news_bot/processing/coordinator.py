import json
import os
import re
from typing import List, Dict
from datetime import datetime, timedelta, date

import google.generativeai as genai
from news_bot.core import config
from news_bot.reporting import google_docs_exporter

# --------------------------
# Step 1: Gemini relevance打分（1~10分）+ 原因解释
# --------------------------

def llm_score_relevance_10point(chinese_text: str, article_title: str = "") -> tuple[int, str]:
    if not chinese_text.strip():
        return 1, "空内容"

    try:
        genai.configure(api_key=config.GEMINI_API_KEY)
        model = genai.GenerativeModel(config.GEMINI_FLASH_MODEL)
    except Exception:
        return 1, "初始化失败"

    prompt = f"""你是一位中文新闻分析师，请判断以下新闻与"纽约大学（NYU）的中国留学生"主题的相关性，并给出 1~10 的整数分数和简要原因。

评分标准：
10 = 与中国留学生紧密相关，是主题核心
7-9 = 与中国学生或国际生显著相关，NYU 是事件主要场景
4-6 = 提及 NYU 或国际学生，但中国学生不是重点
1-3 = 只轻微提到 NYU 或中国，无具体交集

请返回以下格式：
分数：X
原因：...（不超过30字）

新闻标题：{article_title}
新闻正文：
{chinese_text}
"""

    try:
        response = model.generate_content(prompt)
        text = getattr(response, 'text', '').strip()
        match = re.search(r"分数[:：]?\s*(\d+)", text)
        score = int(match.group(1)) if match else 1
        reason = text.split("原因：")[-1].strip() if "原因：" in text else "无解释"
        return max(1, min(score, 10)), reason
    except Exception:
        return 1, "模型异常"

# --------------------------
# Step 2: Gemini润色 refined 中文新闻正文
# --------------------------

def refine_chinese_news_report(text: str, article_title: str = "") -> str:
    if not text.strip():
        return text
    try:
        genai.configure(api_key=config.GEMINI_API_KEY)
        model = genai.GenerativeModel(config.GEMINI_FLASH_MODEL)
    except Exception:
        return text

    prompt = f"""请将以下中文新闻内容进行润色，使其风格正式、逻辑清晰、表达简洁，并符合中文新闻写作规范。
要求：
- 不加入开场白或任何提示语
- 不添加新内容，仅调整语言表达与逻辑
- 去除冗余或重复表达
- 需要确保文章的准确性
- 保留原始新闻结构
- refined_chinese_news_report的正文长度在 200-350 中文汉字，并且不要加入空洞的词汇，更偏向加入具体、重要的细节
- 对不常见的人名、地名、组织名，在首次出现时添加英文括注，如 加拉廷学院 (Gallatin School)、洛根·罗佐斯 (Logan Rozos)

标题参考：{article_title}
原始内容：  
{text}

请输出润色后的新闻正文：
"""

    try:
        response = model.generate_content(prompt)
        return getattr(response, 'text', '').strip()
    except Exception:
        return text

# --------------------------
# Step 3: 润色并提取第一句作为 intro
# --------------------------

def apply_refinement_and_intro(reports: List[Dict]) -> None:
    for report in reports:
        original_text = report.get("refined_chinese_news_report", "")
        if not original_text.strip():
            continue

        article_title = report.get("original_title", "")
        refined_body = refine_chinese_news_report(original_text, article_title)

        # 提取第一句作为 intro（以句号或换行符切分）
        first_sentence = ""
        split_by_punc = re.split(r'(?<=[。！？])\s*', refined_body.strip())
        for sentence in split_by_punc:
            if sentence:
                first_sentence = sentence.strip()
                break

        report["refined_chinese_news_report"] = refined_body
        report["gemini_generated_intro"] = first_sentence

# --------------------------
# Step 4: 主流程
# --------------------------

def process_news_report(input_path: str, output_path: str):
    if not os.path.exists(input_path):
        print(f"文件不存在: {input_path}")
        return

    with open(input_path, 'r', encoding='utf-8') as f:
        reports = json.load(f)

    print(f"正在处理 {len(reports)} 篇新闻...")
    for report in reports:
        refined_text = report.get("refined_chinese_news_report", "")
        title = report.get("original_title", "")
        score, reason = llm_score_relevance_10point(refined_text, title)
        report["relevance_score"] = score
        report["relevance_reason"] = reason

    sorted_reports = sorted(reports, key=lambda x: x["relevance_score"], reverse=True)

    apply_refinement_and_intro(sorted_reports)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(sorted_reports, f, ensure_ascii=False, indent=2)

    print(f"已保存至: {output_path}")

    # --- Export sorted to Google Doc ---
    print("开始导出排序后的结果到 Google Doc...")
    
    # Get the configured date range
    start_date, end_date = config.get_news_date_range()
    
    gdoc_url = google_docs_exporter.update_or_create_news_document(sorted_reports, start_date, end_date)
    if gdoc_url:
        print(f"导出成功: {gdoc_url}")
    else:
        print("导出失败，请检查 API 设置与授权。")

# --------------------------
# Step 5: 执行入口
# --------------------------

if __name__ == "__main__":
    # Get configured date range to find the correct file
    start_date, end_date = config.get_news_date_range()
    
    # Look for files with the date range in the filename
    input_file = None
    reports_dir = "news_reports"
    
    if not os.path.exists(reports_dir):
        print(f"Reports directory '{reports_dir}' does not exist.")
        exit(1)
    
    # Pattern to match files with date range
    pattern = f"weekly_student_news_report_{start_date}_{end_date}"
    
    # Find the most recent file matching the pattern
    for fname in sorted(os.listdir(reports_dir), reverse=True):
        if fname.startswith(pattern) and fname.endswith(".json") and "_sorted" not in fname:
            input_file = os.path.join(reports_dir, fname)
            break
    
    # Fallback to today's date pattern if custom date range file not found
    if input_file is None:
        today = datetime.now().strftime("%Y-%m-%d")
        pattern = f"weekly_student_news_report_{today}"
        
        for fname in sorted(os.listdir(reports_dir), reverse=True):
            if fname.startswith(pattern) and fname.endswith(".json") and "_sorted" not in fname:
                input_file = os.path.join(reports_dir, fname)
                break
    
    # Final fallback to any recent file
    if input_file is None:
        for fname in sorted(os.listdir(reports_dir), reverse=True):
            if fname.startswith("weekly_student_news_report_") and fname.endswith(".json") and "_sorted" not in fname:
                input_file = os.path.join(reports_dir, fname)
                print(f"Warning: Using fallback file (may not match configured date range): {fname}")
                break
    
    if input_file is None:
        print(f"未找到日期范围 {start_date} 到 {end_date} 的新闻摘要文件。")
        print("请先运行 main_orchestrator.py。")
    else:
        output_file = input_file.replace(".json", "_sorted.json")
        print(f"读取输入文件: {input_file}")
        print(f"处理日期范围: {start_date} 到 {end_date}")
        process_news_report(input_file, output_file)