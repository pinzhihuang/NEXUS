# -*- coding: utf-8 -*-
from __future__ import annotations
"""
将 Google Doc（每条新闻用“标题 1”分段）渲染为微信公众号风格长图。
- 自动从 Google Docs 文件名（标题）识别学校 → 注入对应 brand_color
- 每个学校输出到单独文件夹：NYU_Weekly / USC_Weekly / EMORY_Weekly / UCD_Weekly / UBC_Weekly / EDIN_Weekly
- 取消正文底部“来源(Source)”行（仍会用于右上角 credits 小字：已关闭）
- 优先用文档内第一张图片；没有时从 source_url 页面抓取 og:image 等
- 可选生成“资料来源”汇总页
"""

import argparse
from pathlib import Path
from typing import List, Dict, Optional, Tuple

from news_bot.processing.image_generator import (
    generate_image_from_article,
    make_reference_image_from_reports,
)

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/documents.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]
ROOT = Path(__file__).resolve().parents[1]
CREDENTIALS = ROOT / "credentials.json"
TOKEN = ROOT / "token.pickle"

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

SHOW_CREDITS_TOP_RIGHT = False
EXTRACT_COVER_FROM_SOURCE = True

# =================== 学校 → 品牌色 & 文件夹名 ===================
SCHOOL_BRAND_MAP = {
    "NYU": ("#57068c", "New York University (NYU)"),
    "NEW YORK UNIVERSITY": ("#57068c", "New York University (NYU)"),

    "USC": ("#990000", "University of Southern California"),
    "UNIVERSITY OF SOUTHERN CALIFORNIA": ("#990000", "University of Southern California"),

    "EMORY": ("#222c66", "Emory University"),

    "UCD": ("#022851", "University of California, Davis"),
    "UC DAVIS": ("#022851", "University of California, Davis"),
    "UNIVERSITY OF CALIFORNIA, DAVIS": ("#022851", "University of California, Davis"),

    "UBC": ("#002145", "University of British Columbia"),
    "UNIVERSITY OF BRITISH COLUMBIA": ("#002145", "University of British Columbia"),

    "EDINBURGH": ("#041e42", "University of Edinburgh"),
    "UNIVERSITY OF EDINBURGH": ("#041e42", "University of Edinburgh"),
}
DEFAULT_BRAND = ("#57068c", "Default (NYU)")

def pick_brand_from_title(doc_title: str) -> Tuple[str, str]:
    if not doc_title:
        return DEFAULT_BRAND
    t = doc_title.strip().upper()
    for key, val in SCHOOL_BRAND_MAP.items():
        if key in t:
            return val
    return DEFAULT_BRAND

def folder_for_school(matched_school_name: str) -> str:
    n = (matched_school_name or "").upper()
    if "NEW YORK UNIVERSITY" in n:     return "NYU_Weekly"
    if "SOUTHERN CALIFORNIA" in n:     return "USC_Weekly"
    if "EMORY" in n:                   return "EMORY_Weekly"
    if "DAVIS" in n:                   return "UCD_Weekly"
    if "BRITISH COLUMBIA" in n:        return "UBC_Weekly"
    if "EDINBURGH" in n:               return "EDIN_Weekly"
    return "Generic_Weekly"

# =================== Google Doc 读取 ===================
def _get_creds() -> Credentials:
    import pickle
    creds: Optional[Credentials] = None
    if TOKEN.exists():
        with open(TOKEN, "rb") as f:
            creds = pickle.load(f)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS), SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN, "wb") as f:
            pickle.dump(creds, f)
    return creds

def _read_doc(doc_id: str) -> dict:
    service = build("docs", "v1", credentials=_get_creds())
    return service.documents().get(documentId=doc_id).execute()

# =================== 解析工具 ===================
def _get_text(elem) -> str:
    out = []
    for c in elem.get("elements", []):
        txt = c.get("textRun", {}).get("content", "")
        if txt:
            out.append(txt)
    return "".join(out)

def _first_link(elem) -> Optional[str]:
    for c in elem.get("elements", []):
        tr = c.get("textRun")
        if not tr:
            continue
        link = tr.get("textStyle", {}).get("link")
        if link and link.get("url"):
            return link["url"]
    return None

def _first_image_url(elem, inline_objects) -> Optional[str]:
    for c in elem.get("elements", []):
        if "inlineObjectElement" in c:
            obj_id = c["inlineObjectElement"]["inlineObjectId"]
            obj = inline_objects.get(obj_id, {})
            emb = obj.get("inlineObjectProperties", {}).get("embeddedObject", {})
            uri = emb.get("imageProperties", {}).get("contentUri")
            if uri:
                return uri
    return None

def _clean_paragraph_text(raw: str) -> str:
    t = (raw or "").replace("\u3000", " ").strip()
    return t.strip()

def parse_news_from_doc(doc: dict) -> List[Dict]:
    content = doc.get("body", {}).get("content", [])
    inline_objects = doc.get("inlineObjects", {}) or {}

    items: List[Dict] = []
    cur: Optional[Dict] = None

    for blk in content:
        p = blk.get("paragraph")
        if not p:
            continue

        heading = p.get("paragraphStyle", {}).get("namedStyleType", "")
        if heading == "HEADING_1":
            title = _get_text(p).strip()
            if title:
                if cur and (cur.get("title") and cur.get("content").strip()):
                    items.append(cur)
                cur = {"title": title, "content": "", "source_url": "", "cover_image": ""}
            continue

        if cur is not None:
            if not cur.get("cover_image"):
                img = _first_image_url(p, inline_objects)
                if img:
                    cur["cover_image"] = img

            if not cur.get("source_url"):
                lk = _first_link(p)
                if lk:
                    cur["source_url"] = lk

            txt = _get_text(p)
            txt = _clean_paragraph_text(txt)
            if txt:
                low = txt.lower()
                if low.startswith("来源") or low.startswith("source") or low.startswith("来源 (source)"):
                    continue
                if cur["content"]:
                    cur["content"] += "\n\n" + txt
                else:
                    cur["content"] = txt

    if cur and (cur.get("title") and cur.get("content").strip()):
        items.append(cur)

    for it in items:
        it["content"] = it["content"].strip()
    return items

# =================== 封面抓取（从来源页） ===================
def fetch_cover_from_source(page_url: str, timeout: int = 12) -> str:
    if not page_url:
        return ""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X) Chrome/124 Safari/537.36"}
        r = requests.get(page_url, headers=headers, timeout=timeout)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        def _abs(u: str) -> str:
            return urljoin(page_url, (u or "").strip())

        for sel, attr in [
            ('meta[property="og:image"]', "content"),
            ('meta[name="og:image"]', "content"),
            ('meta[property="twitter:image"]', "content"),
            ('meta[name="twitter:image"]', "content"),
            ('meta[itemprop="image"]', "content"),
            ('link[rel="image_src"]', "href"),
        ]:
            tag = soup.select_one(sel)
            if tag and tag.get(attr):
                url = _abs(tag.get(attr))
                if _looks_like_image(url):
                    return url

        for img in soup.find_all("img"):
            src = _abs(img.get("src") or "")
            if not _looks_like_image(src):
                continue
            w = _to_int(img.get("width"))
            h = _to_int(img.get("height"))
            if (w and w < 240) or (h and h < 160):
                continue
            return src
    except Exception:
        pass
    return ""

def _looks_like_image(url: str) -> bool:
    if not url:
        return False
    bad = (".svg", ".gif", "data:image/svg", "sprite", "logo")
    u = url.lower()
    return not any(b in u for b in bad)

def _to_int(x):
    try:
        return int(str(x).strip())
    except Exception:
        return None

# =================== 渲染输出 ===================
def _safe_filename(name: str, limit: int = 60) -> str:
    import re
    s = re.sub(r'[\\/:*?"<>|]+', "_", name).strip()
    return (s[:limit] or "untitled").rstrip("._-")

def render_to_images(items: List[Dict], *, out_dir: str, page_width: int,
                     device_scale: int, title_size: float, body_size: float,
                     brand_color: str, school_name: str = ""):
    Path(out_dir).mkdir(parents=True, exist_ok=True)

    upper_name = (school_name or "").upper()
    # 命中任意一个都算 UCD（放宽以覆盖 "University of California, Davis"）
    is_ucd = ("DAVIS" in upper_name) or ("UC DAVIS" in upper_name) or ("UCD" in upper_name)

    for i, it in enumerate(items, 1):
        title = (it.get("title") or "").strip()
        body  = (it.get("content") or "").strip()
        cover = (it.get("cover_image") or "").strip()
        src   = (it.get("source_url") or "").strip()

        if not cover and EXTRACT_COVER_FROM_SOURCE and src:
            cover = fetch_cover_from_source(src)

        credits = "" if not SHOW_CREDITS_TOP_RIGHT else src
        if not title or not body:
            continue

        # 仅 UCD：奇数蓝(#022851)，偶数黄(#FFBF00)；否则不传该参数
        left_bar_color = None
        if is_ucd:
            left_bar_color = "#022851" if (i % 2 == 1) else "#FFBF00"

        out_path = Path(out_dir) / f"{i:02d}_{_safe_filename(title)}.png"
        generate_image_from_article(
            title=title,
            content=body,
            output_path=str(out_path),
            credits=credits,
            cover_image=cover,
            cover_caption="",
            page_width=page_width,
            device_scale=device_scale,
            title_size=title_size,
            body_size=body_size,
            brand_color=brand_color,        # 全局品牌色（UCD 仍为蓝）
            left_bar_color=left_bar_color,  # UCD 才有交替竖条色；其它学校为 None
        )
        print(f"生成：{out_path}")

# =================== 资料来源页（可选） ===================
def make_sources_page(urls: List[str], out_dir: str, *,
                      filename: str = "00_资料来源.png",
                      top_n: int,
                      page_width: int,
                      device_scale: int,
                      brand_color: str):
    import json, tempfile
    tmp = Path(tempfile.mkstemp(prefix="gdoc_sources_", suffix=".json")[1])
    try:
        payload = [{"source_url": u} for u in urls if u]
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        out = make_reference_image_from_reports(
            sorted_json_path=str(tmp),
            output_dir=out_dir,
            filename=filename,
            top_n=top_n,
            page_width=page_width,
            device_scale=device_scale,
            brand_color=brand_color,   # 汇总页仍用品牌色（不交替）
        )
        print(f"资料来源页：{out}")
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except Exception:
            pass

# =================== CLI ===================
def main():
    ap = argparse.ArgumentParser(description="Render Google Doc (Heading 1 separated) to WeChat-style images")
    ap.add_argument("--doc", required=True, help="Google Doc ID or full URL")
    ap.add_argument("--out", default="wechat_images", help="输出基础目录；会在其下创建学校子目录")
    ap.add_argument("--page-width", type=int, default=540)
    ap.add_argument("--device-scale", type=int, default=4)
    ap.add_argument("--title-size", type=float, default=22.093076923)
    ap.add_argument("--body-size", type=float, default=20)
    ap.add_argument("--top-n", type=int, default=0, help="资料来源页最多展示前 N 条链接（>0 即生成）")
    ap.add_argument("--brand-color", type=str, default="", help="覆盖自动识别的品牌色（如 #990000）")
    args = ap.parse_args()

    # 提取 doc_id
    doc_id = args.doc
    if "/document/d/" in doc_id:
        doc_id = doc_id.split("/document/d/")[1].split("/")[0]

    # 读取文档 & 识别学校/品牌色
    doc = _read_doc(doc_id)
    doc_title = (doc.get("title") or "").strip()
    auto_color, school_name = pick_brand_from_title(doc_title)
    brand_color = args.brand_color.strip() or auto_color
    school_folder = folder_for_school(school_name)

    # 确定学校子目录
    base_out = Path(args.out)
    out_dir = base_out / school_folder
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"学校识别：{school_name}  → brand_color = {brand_color}")
    print(f"输出目录：{out_dir}  (文档标题: {doc_title})")

    items = parse_news_from_doc(doc)
    if not items:
        print("未解析到任何新闻。请确认每条新闻用“标题 1（Heading 1）”开始。")
        return

    print(f"解析到 {len(items)} 条新闻，开始渲染...")
    render_to_images(
        items,
        out_dir=str(out_dir),
        page_width=args.page_width,
        device_scale=args.device_scale,
        title_size=args.title_size,
        body_size=args.body_size,
        brand_color=brand_color,
        school_name=school_name,  # 传入学校名用于 UCD 交替色
    )

    if args.top_n and args.top_n > 0:
        urls = []
        seen = set()
        for it in items:
            u = (it.get("source_url") or "").strip()
            if u and u not in seen:
                seen.add(u)
                urls.append(u)
        if urls:
            make_sources_page(
                urls[: args.top_n],
                out_dir=str(out_dir),
                filename="00_资料来源.png",
                top_n=min(args.top_n, len(urls)),
                page_width=args.page_width,
                device_scale=args.device_scale,
                brand_color=brand_color,
            )
        else:
            print("没有可用来源链接，跳过资料来源页。")

if __name__ == "__main__":
    main()
