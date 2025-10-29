# -*- coding: utf-8 -*-
from __future__ import annotations

"""
从“总表 Google Doc”里抓取目标周（或最新一周）的各学校子文档链接，
并逐个调用 gdoc_to_wechat_images 的渲染逻辑批量生成图片。

功能点：
- --week-title 精确选择某周；不传则自动选择“最新一周”
- 递归解析 paragraph / table / tableOfContents，抓取 smart chip、inlineObject 中的 richLink
- 规范化 Google Doc 链接，仅保留 docId，按 docId 去重
- 渲染失败自动重试
- --list-weeks 仅列出周标题；--debug 打印本周所有解析到的链接
- 方案B导入：优先常规 import，失败时按路径加载同目录 gdoc_to_wechat_images.py
"""

import re
import os
import sys
import time
import argparse
import importlib.util
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# === 关键：让仓库根加入 sys.path（无需再 export PYTHONPATH） ===
REPO_ROOT = Path(__file__).resolve().parents[1]   # 指向仓库根 e.g. .../NEXUS
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# ---------------- 尝试导入渲染模块（方案B 回退） ----------------
try:
    from scripts import gdoc_to_wechat_images as g2w  # type: ignore
except ModuleNotFoundError:
    here = Path(__file__).resolve().parent
    g2w_path = here / "gdoc_to_wechat_images.py"
    if not g2w_path.exists():
        raise
    spec = importlib.util.spec_from_file_location("gdoc_to_wechat_images", str(g2w_path))
    g2w = importlib.util.module_from_spec(spec)  # type: ignore
    assert spec and spec.loader
    spec.loader.exec_module(g2w)  # type: ignore

# ---------------- Google API 读取 ----------------
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/documents.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]
ROOT = REPO_ROOT
CREDENTIALS = ROOT / "credentials.json"
TOKEN = ROOT / "token.pickle"


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


def _resolve_doc_id(url_or_id: str) -> str:
    s = (url_or_id or "").strip()
    if "/document/d/" in s:
        return s.split("/document/d/")[1].split("/")[0]
    return s


# ---------------- 周标题解析 ----------------
# 形如：2025.10.19 - 10.25
WEEK_RE = re.compile(
    r"(?P<y>\d{4})\.(?P<m1>\d{1,2})\.(?P<d1>\d{1,2})\s*-\s*(?P<m2>\d{1,2})\.(?P<d2>\d{1,2})"
)

@dataclass
class WeekBlock:
    title: str
    start: date
    end: date
    links: List[str]


def _extract_week_title_if_any(paragraph: dict) -> Optional[str]:
    """从段落文本中匹配 '2025.10.19 - 10.25' 这种标题。"""
    txt = []
    for el in paragraph.get("elements", []):
        tr = el.get("textRun", {})
        t = tr.get("content", "")
        if t:
            txt.append(t)
    line = "".join(txt).strip()
    if WEEK_RE.search(line):
        return line
    return None


def _parse_week_dates(week_title: str) -> Tuple[date, date]:
    """
    解析 '2025.10.19 - 10.25' → (2025-10-19, 2025-10-25)
    若跨年（如 12 -> 1），自动把结束年 +1。
    """
    m = WEEK_RE.search(week_title)
    if not m:
        raise ValueError(f"无法解析周标题：{week_title}")
    y = int(m.group("y"))
    m1 = int(m.group("m1"))
    d1 = int(m.group("d1"))
    m2 = int(m.group("m2"))
    d2 = int(m.group("d2"))
    y2 = y if m2 >= m1 else y + 1
    return date(y, m1, d1), date(y2, m2, d2)


# ---------------- 链接提取（含表格/TOC，smart chip） ----------------
DOC_URL_RE = re.compile(r"https://docs\.google\.com/document/d/([a-zA-Z0-9_-]+)")

def _clean_doc_url(u: str) -> str:
    """规范化 Doc 链接：抽出 docId 后重组，便于去重。"""
    m = DOC_URL_RE.search(u or "")
    if not m:
        return ""
    doc_id = m.group(1)
    return f"https://docs.google.com/document/d/{doc_id}/edit"


def _extract_all_urls_from_paragraph(paragraph: dict, inline_objects: Dict) -> List[str]:
    urls: List[str] = []

    # A) 普通 textRun link/url/uri
    for el in paragraph.get("elements", []):
        tr = el.get("textRun")
        if tr:
            lnk = tr.get("textStyle", {}).get("link", {})
            if lnk.get("url"):
                urls.append(lnk["url"])
            elif lnk.get("uri"):
                urls.append(lnk["uri"])

    # B) richLink 智能卡片
    for el in paragraph.get("elements", []):
        rich = el.get("richLink")
        if rich:
            props = rich.get("richLinkProperties", {})
            if props.get("uri"):
                urls.append(props["uri"])

    # C) inlineObject → embeddedObject → richLinkProperties.uri
    for el in paragraph.get("elements", []):
        inline = el.get("inlineObjectElement")
        if not inline:
            continue
        obj_id = inline.get("inlineObjectId")
        if not obj_id:
            continue
        obj = inline_objects.get(obj_id, {})
        emb = obj.get("inlineObjectProperties", {}).get("embeddedObject", {})
        props = emb.get("richLinkProperties", {})
        if props.get("uri"):
            urls.append(props["uri"])

    # 规范化并去重
    out, seen = [], set()
    for u in urls:
        cu = _clean_doc_url((u or "").strip())
        if cu and cu not in seen:
            seen.add(cu)
            out.append(cu)
    return out


def _extract_urls_from_structural_element(blk: dict, inline_objects: Dict) -> List[str]:
    """支持 paragraph / table / tableOfContents 递归提取 URL。"""
    urls: List[str] = []

    if "paragraph" in blk:
        urls.extend(_extract_all_urls_from_paragraph(blk["paragraph"], inline_objects))

    if "table" in blk:
        table = blk["table"]
        for row in table.get("tableRows", []):
            for cell in row.get("tableCells", []):
                for se in cell.get("content", []):
                    urls.extend(_extract_urls_from_structural_element(se, inline_objects))

    if "tableOfContents" in blk:
        toc = blk["tableOfContents"]
        for se in toc.get("content", []):
            urls.extend(_extract_urls_from_structural_element(se, inline_objects))

    return urls


def _parse_master_doc_all_weeks(doc: dict) -> List[WeekBlock]:
    """把总表解析成多周：每遇到新的‘周标题’就开始新的一组；循环结束要 flush 最后一组。"""
    content = doc.get("body", {}).get("content", [])
    inline_objects = doc.get("inlineObjects", {}) or {}

    weeks: List[WeekBlock] = []
    cur: Optional[WeekBlock] = None

    for blk in content:
        p = blk.get("paragraph")
        # 1) 识别周标题
        if p:
            week_title = _extract_week_title_if_any(p)
            if week_title:
                if cur and cur.links:
                    weeks.append(cur)
                start, end = _parse_week_dates(week_title)
                cur = WeekBlock(title=week_title, start=start, end=end, links=[])
                continue

        # 2) 递归提取链接（paragraph/table/TOC）
        if cur:
            urls = _extract_urls_from_structural_element(blk, inline_objects)
            if urls:
                cur.links.extend(urls)

    # ★ 收尾：最后一周别漏
    if cur and cur.links:
        weeks.append(cur)

    # 每周内按 docId 去重
    for w in weeks:
        dedup, seen = [], set()
        for u in w.links:
            cu = _clean_doc_url(u)
            if cu and cu not in seen:
                seen.add(cu)
                dedup.append(cu)
        w.links = dedup
    return weeks


def _pick_latest_week(weeks: List[WeekBlock]) -> Optional[WeekBlock]:
    if not weeks:
        return None
    return sorted(weeks, key=lambda w: (w.end, w.start), reverse=True)[0]


# ---------------- 渲染单个子文档（含重试） ----------------
def _process_one_child_doc(doc_url: str, *, out_base: Path, page_width: int,
                           device_scale: int, top_n: int, debug: bool = False):
    doc_id = _resolve_doc_id(doc_url)
    last_err = None
    for attempt in range(1, 3):  # 简单重试 2 次
        try:
            if debug:
                print(f"    -> 获取子文档：{doc_url} (try {attempt})")
            doc = g2w._read_doc(doc_id)
            doc_title = (doc.get("title") or "").strip()

            brand_color, school_name = g2w.pick_brand_from_title(doc_title)
            school_folder = g2w.folder_for_school(school_name)

            out_dir = out_base / school_folder
            out_dir.mkdir(parents=True, exist_ok=True)

            print(f"  → 学校识别：{school_name}  brand_color={brand_color}")
            print(f"  → 输出目录：{out_dir}  (子文档标题: {doc_title})")

            items = g2w.parse_news_from_doc(doc)
            if not items:
                print("  （跳过）未解析到任何新闻。")
                return

            g2w.render_to_images(
                items,
                out_dir=str(out_dir),
                page_width=page_width,
                device_scale=device_scale,
                title_size=22.093076923,
                body_size=20.0,
                brand_color=brand_color,
                school_name=school_name,
            )

            if top_n and top_n > 0:
                urls, seen = [], set()
                for it in items:
                    u = (it.get("source_url") or "").strip()
                    if u and u not in seen:
                        seen.add(u)
                        urls.append(u)
                if urls:
                    g2w.make_sources_page(
                        urls[: top_n],
                        out_dir=str(out_dir),
                        filename="00_资料来源.png",
                        top_n=min(top_n, len(urls)),
                        page_width=page_width,
                        device_scale=device_scale,
                        brand_color=brand_color,
                    )
            return
        except Exception as e:
            last_err = e
            print(f"    !! 渲染失败（try {attempt}）：{e}")
            time.sleep(0.8)
    raise last_err  # 两次都失败才算真正失败


# ---------------- CLI ----------------
def main():
    ap = argparse.ArgumentParser(description="Render latest (or specified) week's school docs from a master Google Doc")
    ap.add_argument("--master-doc", required=True, help="总表 Google Doc ID 或完整 URL")
    ap.add_argument("--out", default="wechat_images", help="输出基础目录；会在其下创建学校子目录")
    ap.add_argument("--page-width", type=int, default=540)
    ap.add_argument("--device-scale", type=int, default=4)
    ap.add_argument("--top-n", type=int, default=10, help="资料来源页最多展示前 N 条链接（>0 即生成）")
    ap.add_argument("--week-title", type=str, default="", help='指定周标题，如 "2025.10.05 - 10.11"')
    ap.add_argument("--list-weeks", action="store_true", help="仅列出总表所有周标题，不渲染")
    ap.add_argument("--debug", action="store_true", help="打印解析到的链接等调试信息")
    args = ap.parse_args()

    master_id = _resolve_doc_id(args.master_doc)
    master = _read_doc(master_id)
    master_title = (master.get("title") or "").strip()
    print(f"总表标题：{master_title}")

    weeks = _parse_master_doc_all_weeks(master)
    if not weeks:
        print("未在总表中解析到任何周标题；请确认格式类似 '2025.10.19 - 10.25'。")
        return

    # 仅列出周标题
    if args.list_weeks:
        print("—— 检出的所有周 ——")
        for w in sorted(weeks, key=lambda x: (x.end, x.start), reverse=True):
            print(f"{w.title}  （{w.start} ~ {w.end}）  links={len(w.links)}")
        return

    # 选择目标周：指定 week-title 优先，否则取最新周
    target: Optional[WeekBlock] = None
    if args.week_title.strip():
        wanted_norm = re.sub(r"\s+", " ", args.week_title.strip())
        for w in weeks:
            if re.sub(r"\s+", " ", w.title.strip()) == wanted_norm:
                target = w
                break
        if not target:
            print(f"没有找到匹配的周标题：{args.week_title}")
            print("可用周标题：")
            for w in sorted(weeks, key=lambda x: (x.end, x.start), reverse=True):
                print("  -", w.title)
            return
    else:
        target = _pick_latest_week(weeks)

    if not target:
        print("没有找到目标周。")
        return

    print(f"选定周：{target.title}  （{target.start} ~ {target.end}）")

    if args.debug:
        print("—— 本周解析到的链接（已规范化并去重） ——")
        for i, u in enumerate(target.links, 1):
            print(f"  [{i:02d}] {u}")

    # 仅保留 Google Docs 子文档链接（target.links 已按 docId 去重过）
    links = [u for u in target.links if "docs.google.com/document/d/" in (u or "")]
    print(f"本周共发现 {len(links)} 个子文档链接。")
    if not links:
        print("没有可用子文档链接。")
        return

    out_base = Path(args.out)
    out_base.mkdir(parents=True, exist_ok=True)

    for idx, link in enumerate(links, 1):
        print(f"[{idx:02d}/{len(links)}] 处理：{link}")
        try:
            _process_one_child_doc(
                link,
                out_base=out_base,
                page_width=args.page_width,
                device_scale=args.device_scale,
                top_n=args.top_n,
                debug=args.debug,
            )
        except Exception as e:
            print(f"  （跳过）渲染失败：{e}")

    print("全部完成。")


if __name__ == "__main__":
    # 运行示例：
    #   python script/gdoc_master_latest_to_images.py \
    #     --master-doc "https://docs.google.com/document/d/xxx/edit?tab=t.0" \
    #     --out wechat_images --page-width 540 --device-scale 4 --top-n 10 \
    #     --week-title "2025.10.12 - 10.18" --debug
    main()
