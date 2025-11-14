# scripts/run_single_article.py

from news_bot.processing.article_handler import fetch_article_and_verify
from news_bot.generation.summarizer import summarize_english
from news_bot.localization.translator import generate_chinese_news_package
from news_bot.utils.file_manager import save_report

URL = "https://www.latimes.com/sports/dodgers/story/2025-11-01/dodgers-championship-parade-rally-monday"

def main():
    # 1. 抓原文 + 基本验证（时间、类型、相关性）
    article = fetch_article_and_verify(URL)
    if not article.is_suitable:
        print("Article not suitable according to NEXUS rules.")
        return

    # 2. 英文摘要
    summary_en = summarize_english(
        article_text=article.text,
        source="Los Angeles Times",
        pub_date=article.pub_date,
    )

    # 3. 中文标题 + 初稿 + 精修稿
    cn_pkg = generate_chinese_news_package(
        summary_en=summary_en,
        source="洛杉矶时报",
        pub_date=article.pub_date,
        audience_desc="在洛杉矶的国际学生群体"
    )

    # 4. 保存结构化结果
    data = {
        "source_url": URL,
        "source": "Los Angeles Times",
        "pub_date": str(article.pub_date),
        "summary_en": summary_en,
        "cn_title": cn_pkg.cn_title,
        "cn_initial": cn_pkg.cn_initial,
        "cn_refined": cn_pkg.cn_refined,
    }
    save_report(data)

if __name__ == "__main__":
    main()
