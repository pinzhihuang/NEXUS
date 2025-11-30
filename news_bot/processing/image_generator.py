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
# 这里的 parents[1] 指向 news_bot/ 目录；模板放在 news_bot/templates 下
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
            "需要: news_bot/templates/weixin_article_template.html（模板变量："
            "font_src/page_width/min_height/title_size/body_size/brand_color/left_bar_color/"
            "title/body/credits/marker_label/cover_image/cover_caption）"
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
    # 1. Check environment variables first
    for key in ("PUPPETEER_EXECUTABLE_PATH", "PYPPETEER_EXECUTABLE_PATH", "CHROME_PATH"):
        p = os.environ.get(key)
        if p and Path(p).exists():
            print(f"[chrome_path] Found via env var {key}: {p}")
            return p
    
    import sys
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
        # Special handling for Nix store paths (Railway/Nixpacks) - check FIRST
        nix_chromium_paths = []
        try:
            import glob
            nix_chromium_paths = glob.glob("/nix/store/*/bin/chromium")
            if nix_chromium_paths:
                print(f"[chrome_path] Found {len(nix_chromium_paths)} Nix Chromium paths")
                for path in nix_chromium_paths:
                    print(f"[chrome_path]   - {path}")
        except Exception as e:
            print(f"[chrome_path] Error globbing Nix paths: {e}")
        
        candidates = [
            shutil.which("chromium-browser"),  # Nixpacks/Railway
            shutil.which("chromium"),          # Nixpacks/Railway
            shutil.which("google-chrome"),
            shutil.which("chrome"),
            "/usr/bin/chromium-browser",
            "/usr/bin/chromium",
            "/usr/bin/google-chrome",
        ]
        
        # Prepend Nix paths to candidates
        if nix_chromium_paths:
            candidates = nix_chromium_paths + candidates
    
    print(f"[chrome_path] Checking {len(candidates)} candidate paths...")
    for c in candidates:
        if c and Path(c).exists():
            print(f"[chrome_path] ✅ Found working path: {c}")
            return c
        elif c:
            print(f"[chrome_path] ❌ Path doesn't exist: {c}")
    
    print("[chrome_path] ⚠️  No Chrome/Chromium found in any standard location")
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
    title_size: float = 22.093076923,
    body_size: float = 20.0,
    marker_label: str = "",
    brand_color: str = "#57068c",
    left_bar_color: str | None = None,   # ★ 关键：把交替色也传到模板
) -> str:
    tpl = _ensure_article_template()
    body_html = _to_html(content)
    cover_src = _embed_image_as_data_uri(cover_image) if cover_image else ""
    font_src = _font_data_uri() or (FONTS_DIR / "SourceHanSerifSC-VF.otf").resolve().as_uri()

    # 可选调试：设置环境变量 WXIMG_DEBUG=1 可打印颜色
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
        left_bar_color=left_bar_color,   # ★ 关键：传给模板（CSS 用 var(--left-bar-color)）
    )

# ================= HTML → PNG =================
async def _html_to_png(html: str, out_path: Path, page_width: int, device_scale: int) -> None:
    """Convert HTML to PNG using Puppeteer/Chromium."""
    import threading
    print(f"[_html_to_png] Starting in thread: {threading.current_thread().name}")
    
    from pyppeteer import launch
    chrome_path = _guess_chrome_path()
    
    launch_kwargs = dict(
        headless=True,
        # ★ Critical fix for Flask threaded environment:
        # Disable signal handlers to avoid "signal only works in main thread" error
        handleSIGINT=False,
        handleSIGTERM=False,
        handleSIGHUP=False,
        args=[
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--disable-web-security",
            "--allow-file-access-from-files",
            "--disable-dev-profile",
            "--single-process",  # Helps in constrained environments
            "--disable-software-rasterizer",
            "--disable-extensions",
            "--disable-background-networking",
            "--disable-default-apps",
            "--disable-sync",
            "--disable-translate",
            "--hide-scrollbars",
            "--metrics-recording-only",
            "--mute-audio",
            "--no-first-run",
            "--safebrowsing-disable-auto-update",
            "--disable-crash-reporter",
            "--disable-logging",
            "--disable-permissions-api",
        ],
    )
    
    if chrome_path:
        launch_kwargs["executablePath"] = chrome_path
        print(f"[puppeteer] Using system browser: {chrome_path}")
    else:
        print("[puppeteer] ⚠️  No system browser found. Will try bundled Chromium (may fail in Railway).")
        print("[puppeteer] 💡 If this fails, ensure nixpacks.toml includes chromium in nixPkgs")

    print(f"[_html_to_png] About to call launch() with kwargs: {list(launch_kwargs.keys())}")
    print(f"[_html_to_png] Signal handler flags: SIGINT={launch_kwargs['handleSIGINT']}, SIGTERM={launch_kwargs['handleSIGTERM']}, SIGHUP={launch_kwargs['handleSIGHUP']}")
    
    try:
        browser = await launch(**launch_kwargs)
        print("[_html_to_png] Browser launched successfully")
    except Exception as e:
        print(f"[_html_to_png] ❌ Browser launch FAILED: {type(e).__name__}: {e}")
        if not chrome_path:
            print("[_html_to_png] 💡 TIP: Install Chromium via nixpacks.toml or set PUPPETEER_EXECUTABLE_PATH")
        raise
    
    try:
        print("[_html_to_png] Creating new page...")
        page = await browser.newPage()
        
        print("[_html_to_png] Setting viewport...")
        await page.setViewport({
            "width": page_width,
            "height": 1500,
            "deviceScaleFactor": device_scale,
        })
        
        print("[_html_to_png] Setting content...")
        await page.setContent(html)
        
        print("[_html_to_png] Waiting for selector #page-root...")
        await page.waitForSelector("#page-root", {"timeout": 15000})
        
        print("[_html_to_png] Waiting 800ms...")
        await page.waitFor(800)
        
        print(f"[_html_to_png] Taking screenshot to {out_path}...")
        await page.screenshot({"path": str(out_path), "fullPage": True})
        print("[_html_to_png] Screenshot saved successfully")
    finally:
        print("[_html_to_png] Closing browser...")
        await browser.close()
        print("[_html_to_png] Browser closed")

def _run_async_thread_safe(coro):
    """
    Run async code in a thread-safe manner.
    Works in both main thread and worker threads (e.g., Flask request handlers).
    
    This avoids the 'signal only works in main thread' error by:
    1. Always creating a fresh event loop for the current thread
    2. Not relying on asyncio.run() which sets up signal handlers
    """
    import threading
    print(f"[_run_async_thread_safe] Starting in thread: {threading.current_thread().name}")
    
    # Always create a new event loop to avoid signal handler issues
    print("[_run_async_thread_safe] Creating new event loop...")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    print(f"[_run_async_thread_safe] Event loop created and set for thread {threading.current_thread().name}")
    
    try:
        print("[_run_async_thread_safe] Running coroutine...")
        result = loop.run_until_complete(coro)
        print("[_run_async_thread_safe] Coroutine completed successfully")
        return result
    except Exception as e:
        print(f"[_run_async_thread_safe] ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        # Clean up the loop
        try:
            # Cancel any pending tasks
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            # Run the loop briefly to allow tasks to finish cancelling
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        except Exception:
            pass
        finally:
            loop.close()

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
    title_size: float = 22.093076923,
    body_size: float = 20.0,
    crop_bottom_keep: int = CROP_BOTTOM_KEEP,
    crop_keep_left: int = CROP_KEEP_LEFT,
    crop_keep_right: int = CROP_KEEP_RIGHT,
    crop_keep_top: int = CROP_KEEP_TOP,
    brand_color: str = "#57068c",
    left_bar_color: str | None = None,   # ★ 关键：从上游接受交替色
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
        left_bar_color=left_bar_color,   # ★ 关键：继续传到模板
    )
    
    print("[generate_image_from_article] HTML rendered, calling _run_async_thread_safe...")
    _run_async_thread_safe(_html_to_png(html, out, page_width, device_scale))
    
    print("[generate_image_from_article] Screenshot complete, cropping...")
    _smart_crop_bottom_keep(
        out,
        keep_px=crop_bottom_keep, keep_left=crop_keep_left,
        keep_right=crop_keep_right, keep_top=crop_keep_top
    )
    
    print(f"[generate_image_from_article] ✅ Complete: {out}")
    return str(out)

# =============== 对外函数：参考来源页 =================
def make_reference_image_from_reports(
    sorted_json_path: str,
    output_dir: str = "wechat_images",
    filename: str = "00_资料来源.png",
    top_n: int = 5,
    page_width: int = 540,
    device_scale: int = 4,
    template_path: str | None = None,
    min_height: int = DEFAULT_MIN_HEIGHT,
    brand_color: str = "#57068c",
) -> str:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / filename

    with open(sorted_json_path, "r", encoding="utf-8") as f:
        reports = json.load(f)
    reports = (reports or [])[:top_n]

    urls: List[str] = []
    for r in reports:
        url = (r.get("source_url") or "") or (r.get("verification_details", {}).get("url") or "")
        url = (url or "").strip()
        if url:
            urls.append(url)

    font_src = _font_data_uri() or (FONTS_DIR / "SourceHanSerifSC-VF.otf").resolve().as_uri()
    tpl = _ensure_reference_template(template_path)
    html = tpl.render(
        font_src=font_src,
        page_width=page_width,
        min_height=min_height,
        urls=urls,
        brand_color=brand_color,
    )
    _run_async_thread_safe(_html_to_png(html, out_path, page_width, device_scale))
    _smart_crop_bottom_keep(
        out_path,
        keep_px=CROP_BOTTOM_KEEP,
        keep_left=CROP_KEEP_LEFT,
        keep_right=CROP_KEEP_RIGHT,
        keep_top=CROP_KEEP_TOP,
    )
    return str(out_path)
