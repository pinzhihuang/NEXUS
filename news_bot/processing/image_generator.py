# -*- coding: utf-8 -*-
"""
image_generator.py (brand_color + left_bar_color aware)
"""
from __future__ import annotations
import asyncio
import base64
import os
import re
import shutil
import json
from pathlib import Path
from typing import List, Optional
from jinja2 import Template
import markdown2
from PIL import Image, ImageChops

# ----------------- 路径与参数 -----------------
ROOT_DIR = Path(__file__).resolve().parents[1]
TEMPLATE_DIR       = ROOT_DIR / "templates"
TEMPLATE_ARTICLE   = TEMPLATE_DIR / "weixin_article_template.html"
TEMPLATE_REFERENCE = TEMPLATE_DIR / "weixin_reference_template.html"
FONTS_DIR          = ROOT_DIR / "assets" / "fonts"

DEFAULT_PAGE_WIDTH   = 540
DEFAULT_MIN_HEIGHT   = 2200
DEFAULT_DEVICE_SCALE = 2

# 裁切策略：仅裁底部；左右/上固定留白
CROP_BOTTOM_KEEP = 110
CROP_KEEP_LEFT   = 50
CROP_KEEP_RIGHT  = 50
CROP_KEEP_TOP    = 50
# ---------------------------------------------

# ================= 模板 & 工具 =================
def _ensure_article_template() -> Template:
    if not TEMPLATE_ARTICLE.exists():
        raise FileNotFoundError(
            f"[image_generator] 模板不存在: {TEMPLATE_ARTICLE}\n"
            "需要: news_bot/templates/weixin_article_template.html"
        )
    return Template(TEMPLATE_ARTICLE.read_text(encoding="utf-8"))

def _ensure_reference_template(template_path: Optional[str | Path]) -> Template:
    if template_path:
        p = Path(template_path)
        if not p.exists():
            raise FileNotFoundError(f"[image_generator] 找不到参考页模板: {p}")
        return Template(p.read_text(encoding="utf-8"))
    if not TEMPLATE_REFERENCE.exists():
        raise FileNotFoundError(
            f"[image_generator] 模板不存在: {TEMPLATE_REFERENCE}\n"
            "需要: news_bot/templates/weixin_reference_template.html"
        )
    return Template(TEMPLATE_REFERENCE.read_text(encoding="utf-8"))

def _to_html(text: str) -> str:
    if not text:
        return ""
    cleaned = re.sub(r'(?<!\n)\n(?!\n)', ' ', text.strip())
    return markdown2.markdown(cleaned)

def _embed_image_as_data_uri(image_path_or_url: str) -> str:
    if not image_path_or_url:
        return ""
    if re.match(r"^https?://", image_path_or_url, re.I):
        return image_path_or_url
    p = Path(image_path_or_url)
    if not p.exists():
        return ""
    b64 = base64.b64encode(p.read_bytes()).decode("ascii")
    ext = (p.suffix or "").lower()
    mime = "image/png" if ext == ".png" else "image/jpeg"
    return f"data:{mime};base64,{b64}"

def _font_data_uri() -> str:
    vf = FONTS_DIR / "SourceHanSerifSC-VF.otf"
    try:
        if vf.exists():
            b64 = base64.b64encode(vf.read_bytes()).decode("ascii")
            return f"data:font/otf;base64,{b64}"
    except Exception:
        pass
    return ""  # 找不到就返回空，后续兜底使用 file:// 绝对路径

def _guess_chrome_path() -> str | None:
    """Find Chrome/Chromium executable path across different environments."""
    import subprocess
    
    print("[chrome_path] ========================================")
    print("[chrome_path] Starting Chromium detection process")
    print("[chrome_path] ========================================")
    
    # 1. Check environment variables first
    print("[chrome_path] Step 1: Checking environment variables...")
    for key in ("PUPPETEER_EXECUTABLE_PATH", "PYPPETEER_EXECUTABLE_PATH", "CHROME_PATH"):
        p = os.environ.get(key)
        print(f"[chrome_path]   ${key} = {p if p else 'NOT SET'}")
        if p and Path(p).exists():
            print(f"[chrome_path] Found via env var {key}: {p}")
            return p
        elif p:
            print(f"[chrome_path] ⚠️  Env var {key} is set but path doesn't exist: {p}")
    
    import sys
    print(f"[chrome_path] Step 2: Platform = {sys.platform}")
    
    if sys.platform == "darwin":  # macOS
        candidates = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
        ]
    elif sys.platform.startswith("win"):
        candidates = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        ]
    else:  # linux (Railway, Docker, etc.)
        print("[chrome_path] Step 3: Linux detected - searching for Chromium...")
        
        # Check if /nix/store exists
        nix_store_exists = Path("/nix/store").exists()
        print(f"[chrome_path]   /nix/store exists: {nix_store_exists}")
        
        if nix_store_exists:
            try:
                print("[chrome_path]   Listing /nix/store contents (first 10)...")
                nix_entries = list(Path("/nix/store").iterdir())[:10]
                for entry in nix_entries:
                    print(f"[chrome_path]     - {entry.name}")
            except Exception as e:
                print(f"[chrome_path]   ⚠️  Could not list /nix/store: {e}")
        
        # Special handling for Nix store paths (Railway/Nixpacks) - check FIRST
        nix_chromium_paths = []
        print("[chrome_path] Step 4: Searching Nix store with glob...")
        try:
            import glob
            print("[chrome_path]   Running: glob.glob('/nix/store/*/bin/chromium')")
            nix_chromium_paths = glob.glob("/nix/store/*/bin/chromium")
            print(f"[chrome_path]   Result: {len(nix_chromium_paths)} paths found")
            if nix_chromium_paths:
                for path in nix_chromium_paths:
                    print(f"[chrome_path]     - {path}")
        except Exception as e:
            print(f"[chrome_path]   ❌ Error globbing Nix paths: {e}")
            import traceback
            traceback.print_exc()
        
        # Try alternative: subprocess find
        if not nix_chromium_paths and nix_store_exists:
            print("[chrome_path] Step 5: Trying subprocess find...")
            try:
                result = subprocess.run(
                    ["find", "/nix/store", "-path", "*/bin/chromium", "-type", "f"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0 and result.stdout.strip():
                    found = result.stdout.strip().split('\n')
                    print(f"[chrome_path]   Found {len(found)} paths via find:")
                    for path in found[:5]:  # Show first 5
                        print(f"[chrome_path]     - {path}")
                    if found:
                        nix_chromium_paths = found
                else:
                    print(f"[chrome_path]   find returned: {result.returncode}")
                    print(f"[chrome_path]   stderr: {result.stderr}")
            except Exception as e:
                print(f"[chrome_path]   ❌ Error with find command: {e}")
        
        print("[chrome_path] Step 6: Checking shutil.which()...")
        candidates = [
            shutil.which("chromium-browser"),
            shutil.which("chromium"),
            shutil.which("google-chrome"),
            shutil.which("chrome"),
            "/usr/bin/chromium-browser",
            "/usr/bin/chromium",
            "/usr/bin/google-chrome",
        ]
        
        for i, c in enumerate(candidates[:4]):  # First 4 are which() results
            print(f"[chrome_path]   shutil.which result {i}: {c if c else 'None'}")
        
        # Prepend Nix paths to candidates
        if nix_chromium_paths:
            print(f"[chrome_path] Prepending {len(nix_chromium_paths)} Nix paths to candidates")
            candidates = nix_chromium_paths + candidates
    
    print(f"[chrome_path] Step 7: Checking {len(candidates)} total candidate paths...")
    for i, c in enumerate(candidates):
        if c:
            exists = Path(c).exists()
            print(f"[chrome_path]   [{i+1}/{len(candidates)}] {c} - exists={exists}")
            if exists:
                print(f"[chrome_path] SUCCESS: Found working path: {c}")
                return c
        else:
            print(f"[chrome_path]   [{i+1}/{len(candidates)}] (None/empty)")
    
    print("[chrome_path] ========================================")
    print("[chrome_path] ❌ FAILED: No Chrome/Chromium found")
    print("[chrome_path] ========================================")
    return None

# ================= 渲染 HTML（正文） =================
def _render_html(
    title: str,
    content: str,
    *,
    credits: str = "",
    cover_image: str = "",
    cover_caption: str = "",
    page_width: int = DEFAULT_PAGE_WIDTH,
    min_height: int = DEFAULT_MIN_HEIGHT,
    title_size: float = 22.5,
    body_size: float = 22.5,
    marker_label: str = "",
    brand_color: str = "#57068c",
    left_bar_color: str | None = None,   # 交替色传入模板
) -> str:
    tpl = _ensure_article_template()
    body_html = _to_html(content)
    cover_src = _embed_image_as_data_uri(cover_image) if cover_image else ""
    font_src = _font_data_uri() or (FONTS_DIR / "SourceHanSerifSC-VF.otf").resolve().as_uri()

    if os.environ.get("WXIMG_DEBUG"):
        print(f"[image_generator] brand_color={brand_color} left_bar_color={left_bar_color}")

    return tpl.render(
        font_src=font_src,
        page_width=page_width,
        min_height=min_height,
        title_size=title_size,
        body_size=body_size,
        title=title,
        body=body_html,
        credits=credits,
        marker_label=marker_label,
        cover_image=cover_src,
        cover_caption=cover_caption,
        brand_color=brand_color,
        left_bar_color=left_bar_color,
    )

# ================= HTML → PNG (Using Playwright) =================
def _html_to_png_sync(html: str, out_path: Path, page_width: int, device_scale: int) -> None:
    """Convert HTML to PNG using Playwright (synchronous API - more stable than pyppeteer)."""
    import threading
    print(f"[_html_to_png] Starting in thread: {threading.current_thread().name}")
    
    from playwright.sync_api import sync_playwright
    
    print("[_html_to_png] Launching Playwright...")
    
    # Try to find system Chrome/Chromium as fallback
    chrome_path = _guess_chrome_path()
    
    launch_kwargs = {
        "headless": True,
        "args": [
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--disable-web-security",
            "--allow-file-access-from-files",
        ],
    }
    
    # Use system Chrome if available (important for Railway/Docker deployments)
    if chrome_path:
        launch_kwargs["executable_path"] = chrome_path
        print(f"[_html_to_png] Using system browser: {chrome_path}")
    else:
        print("[_html_to_png] Using Playwright's bundled Chromium")
    
    with sync_playwright() as p:
        print("[_html_to_png] Launching Chromium browser...")
        browser = p.chromium.launch(**launch_kwargs)
        print("[_html_to_png] Browser launched successfully")
        
        try:
            print("[_html_to_png] Creating new page...")
            page = browser.new_page(
                viewport={"width": page_width, "height": 1500},
                device_scale_factor=device_scale,
            )
            
            print("[_html_to_png] Setting content...")
            page.set_content(html)
            
            print("[_html_to_png] Waiting for selector #page-root...")
            page.wait_for_selector("#page-root", timeout=15000)
            
            print("[_html_to_png] Waiting 800ms for rendering...")
            page.wait_for_timeout(800)
            
            print(f"[_html_to_png] Taking screenshot to {out_path}...")
            page.screenshot(path=str(out_path), full_page=True)
            print("[_html_to_png] Screenshot saved successfully")
        finally:
            print("[_html_to_png] Closing browser...")
            browser.close()
            print("[_html_to_png] Browser closed")

# ================= 智能裁剪 =================
def _smart_crop_bottom_keep(
    img_path: Path,
    keep_px: int = CROP_BOTTOM_KEEP,
    keep_left: int = CROP_KEEP_LEFT,
    keep_right: int = CROP_KEEP_RIGHT,
    keep_top: int = CROP_KEEP_TOP,
) -> None:
    try:
        im = Image.open(img_path).convert("RGB")
        w, h = im.size
        bg = Image.new(im.mode, (w, h), (255, 255, 255))
        diff = ImageChops.difference(im, bg)
        bbox = diff.getbbox()
        if not bbox:
            return
        _, _, _, content_bottom = bbox
        left   = max(0, keep_left)
        top    = max(0, keep_top)
        right  = min(w, w - keep_right)
        bottom = min(h, content_bottom + keep_px)
        if right - left >= 20 and bottom - top >= 20:
            im.crop((left, top, right, bottom)).save(img_path)
    except Exception:
        pass

# ================== 对外函数：正文长图 ==================
def generate_image_from_article(
    *,
    title: str,
    content: str,
    output_path: str,
    subtitle: str = "",
    cover_image: str = "",
    cover_caption: str = "",
    credits: str = "",
    marker_label: str = "",
    page_width: int = DEFAULT_PAGE_WIDTH,
    min_height: int = DEFAULT_MIN_HEIGHT,
    device_scale: int = DEFAULT_DEVICE_SCALE,
    title_size: float = 22.5,
    body_size: float = 22.5,
    crop_bottom_keep: int = CROP_BOTTOM_KEEP,
    crop_keep_left: int = CROP_KEEP_LEFT,
    crop_keep_right: int = CROP_KEEP_RIGHT,
    crop_keep_top: int = CROP_KEEP_TOP,
    brand_color: str = "#57068c",
    left_bar_color: str | None = None,   # 从上游接受交替色
) -> str:
    """Generate a WeChat-style article image from text content."""
    import threading
    print(f"[generate_image_from_article] Called from thread: {threading.current_thread().name}")
    print(f"[generate_image_from_article] Output path: {output_path}")
    print(f"[generate_image_from_article] Title: {title[:50]}...")
    
    out = Path(output_path).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    print("[generate_image_from_article] Rendering HTML...")
    html = _render_html(
        title=title.strip(),
        content=content.strip(),
        credits=credits.strip(),
        cover_image=cover_image.strip(),
        cover_caption=cover_caption.strip(),
        page_width=page_width,
        min_height=DEFAULT_MIN_HEIGHT if min_height is None else min_height,
        title_size=title_size,
        body_size=body_size,
        marker_label=marker_label.strip(),
        brand_color=brand_color,
        left_bar_color=left_bar_color,
    )
    
    print("[generate_image_from_article] HTML rendered, calling Playwright...")
    _html_to_png_sync(html, out, page_width, device_scale)
    
    print("[generate_image_from_article] Screenshot complete, cropping...")
    _smart_crop_bottom_keep(
        out,
        keep_px=crop_bottom_keep, keep_left=crop_keep_left,
        keep_right=crop_keep_right, keep_top=crop_keep_top
    )
    
    print(f"[generate_image_from_article] Complete: {out}")
    return str(out)

# ----------------- 多来源提取工具 -----------------
_URL_RE = re.compile(r"https?://[^\s\)\]\}，。；、]+", re.IGNORECASE)

def _extract_urls_from_report(r: dict) -> list[str]:
    """从一篇 report 中抓取尽可能多的来源链接，顺序去重。"""
    candidates: list[str] = []

    # 结构化字段
    if isinstance(r.get("source_urls"), list):
        candidates.extend([u for u in r["source_urls"] if isinstance(u, str)])
    if isinstance(r.get("source_url"), str):
        candidates.append(r["source_url"])

    v = r.get("verification_details") or {}
    if isinstance(v.get("url"), str):
        candidates.append(v["url"])
    if isinstance(v.get("urls"), list):
        candidates.extend([u for u in v["urls"] if isinstance(u, str)])

    # 从常见文本字段扫描 http(s) 链接
    for fld in [
        "final_cn_report", "cn_report", "zh_report",
        "en_summary", "summary", "body", "content",
    ]:
        txt = r.get(fld) or ""
        if isinstance(txt, str) and txt:
            candidates.extend(_URL_RE.findall(txt))

    # 去重（保序）
    cleaned: list[str] = []
    seen: set[str] = set()
    for u in candidates:
        u = u.strip().strip("，。,.;:)]}>）】」』")
        if u and u not in seen:
            seen.add(u)
            cleaned.append(u)
    return cleaned

# =============== 对外函数：参考来源页（修复版） =================
def make_reference_image_from_reports(
    sorted_json_path: str,
    output_dir: str = "wechat_images",
    filename: str = "00_资料来源.png",
    top_n: int = 5,                     # top_n=每周选取前N篇；<=0 表示不限量
    page_width: int = 540,
    device_scale: int = 4,
    template_path: str | None = None,
    min_height: int = DEFAULT_MIN_HEIGHT,
    brand_color: str = "#57068c",
) -> str:
    """把选中的若干篇报告里的所有来源链接汇总成一张图片。
       - 支持一篇报告多个来源
       - top_n<=0 时包含全部报告
       - 去重但保持出现顺序
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / filename

    with open(sorted_json_path, "r", encoding="utf-8") as f:
        reports = json.load(f) or []

    subset = reports if top_n <= 0 else reports[:top_n]

    urls: list[str] = []
    seen: set[str] = set()
    for r in subset:
        for u in _extract_urls_from_report(r):
            if u and u not in seen:
                seen.add(u)
                urls.append(u)

    font_src = _font_data_uri() or (FONTS_DIR / "SourceHanSerifSC-VF.otf").resolve().as_uri()
    tpl = _ensure_reference_template(template_path)
    html = tpl.render(
        font_src=font_src,
        page_width=page_width,
        min_height=min_height,
        urls=urls,
        brand_color=brand_color,
    )
    _html_to_png_sync(html, out_path, page_width, device_scale)
    _smart_crop_bottom_keep(
        out_path,
        keep_px=CROP_BOTTOM_KEEP,
        keep_left=CROP_KEEP_LEFT,
        keep_right=CROP_KEEP_RIGHT,
        keep_top=CROP_KEEP_TOP,
    )
    return str(out_path)
