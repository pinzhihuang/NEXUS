 NEXUS – Google Docs → WeChat-style Images (Render Guide)

> Batch render WeChat-style images from Google Docs. Works for single school docs and for a weekly master index that links to per‑school docs (supports Smart Chips and normal hyperlinks; parses paragraphs, tables, and TOC).
---

## Overview

- **Shell entrypoints**:
  - `scripts/render_latest_week.sh`: One-click render of ALL schools for the latest week found in the master doc.
  - `scripts/render_week.sh`: One-click render for either the latest week or an explicitly named week title.
  - `scripts/render_single_doc.sh`: One-click render for a single Google Doc (one school’s weekly doc).
- **Python engines**:
  - `scripts/gdoc_master_latest_to_images.py`: Parses the master weekly index, finds the target week’s per‑school docs, and batch-calls the single-doc renderer.
  - `scripts/gdoc_to_wechat_images.py`: Renders a single weekly doc into multiple WeChat-style images.

Output is written under `wechat_images/<School_Weekly>/` with consistent file naming. Templates/layout are preserved. For UCD, the left bar alternates blue/yellow for odd/even items automatically.

---

## Prerequisites

- macOS or Linux recommended
- Python 3.10+
- Google Docs API + Google Drive API enabled
- Chrome/Chromium installed
- Place `credentials.json` at the repo root for OAuth. On first run, an OAuth flow creates `token.pickle`.

### Install

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# Minimal set if needed:
pip install google-api-python-client google-auth google-auth-oauthlib \
            beautifulsoup4 requests pillow packaging
```

### OAuth (one-time)

1. Enable “Google Docs API” and “Google Drive API”.
2. Create OAuth 2.0 credentials (Desktop App) and save as `NEXUS/credentials.json`.
3. First run opens browser; after consent, `NEXUS/token.pickle` is created.
4. If auth fails later, delete `token.pickle` and retry.

---

## What each script does

### scripts/gdoc_to_wechat_images.py (single-doc renderer)

- Reads one Google Doc and splits news items by Heading 1 sections.
- **Improved Image Logic**: Priority is given to inline images in the doc. If missing, it automatically attempts to fetch a cover from the source page (`og:image`, `twitter:image`, etc.). If neither exists, it renders without a cover.
- Brand color and school output subfolder are inferred from the doc title; can be overridden.
- **Folders**: Automatically handles path normalization to prevent double-nested folders (e.g., `EMORY_Weekly/EMORY_Weekly/`).
- **Cleanup**: Automatically creates and deletes temporary JSON files in the system temp directory during execution.
- UCD special handling: left bar alternates blue `#022851` (odd) and yellow `#FFBF00` (even).
- Optional “资料来源” page (`00_资料来源.png`) lists top N unique source links.

Key options:

```bash
python scripts/gdoc_to_wechat_images.py \
  --doc <docId_or_full_URL> \
  --out wechat_images \
  --page-width 540 \
  --device-scale 4 \
  --top-n 10 \
  --no-images              # optional: skip all image fetching/rendering
  --brand-color "#990000"  # optional override
```

### scripts/gdoc_master_latest_to_images.py (master → batch renderer)

- Reads a weekly master Google Doc that contains per‑school doc links.
- **Flexible Date Parsing**: Supports both `YYYY.MM.DD - MM.DD` and `YYYY.MM.DD - YYYY.MM.DD` formats.
- Extracts links from paragraphs, tables, and TOC; supports Smart Chips and rich links inside inline objects.
- Normalizes links by docId and de‑duplicates.
- Chooses the latest week by default, or a specified week via `--week-title`.
- Invokes the single‑doc renderer per child doc and optionally creates a sources page per school.

Key options:

```bash
python scripts/gdoc_master_latest_to_images.py \
  --master-doc <master_docId_or_URL> \
  --out wechat_images \
  --page-width 540 \
  --device-scale 4 \
  --top-n 10 \
  --week-title "2025.10.12 - 10.18" \
  --debug
```

---

## One‑click shell wrappers

All wrappers automatically:
- cd to repo root
- activate `.venv` if present
- export `PYTHONPATH` as repo root (so imports work)

Make scripts executable (first time only). Alternatively, you can always run via `bash scripts/<name>.sh` without `chmod`.

```bash
chmod +x scripts/*.sh
```

### scripts/render_single_doc.sh

Render one weekly doc. If no argument is provided, the scripts will prompt for it.

```bash
# Basic Usage
scripts/render_single_doc.sh <docId_or_URL>

# Skip images (faster)
scripts/render_single_doc.sh <docId_or_URL> no-images

# Custom Brand Color
scripts/render_single_doc.sh <docId_or_URL> "#990000"
```

Environment overrides:
- `OUT_DIR` (default: `wechat_images`)
- `PAGE_WIDTH` (default: `540`)
- `DEVICE_SCALE` (default: `4`)
- `TOP_N` (default: `10`)
- `BRAND_COLOR` (default: auto by title)

### scripts/render_week.sh

Render either the latest week or an exact week title from the master doc. If no mode is provided, you will be prompted.

```bash
# Latest week
scripts/render_week.sh latest

# Exact week
scripts/render_week.sh exact "2025.10.12 - 10.18"
```

Defaults used inside:
- `MASTER_DOC` points to your master index URL
- `OUT_DIR=wechat_images`, `PAGE_WIDTH=540`, `DEVICE_SCALE=4`, `TOP_N=10`

To change the master doc URL, edit `MASTER_DOC` at the top of:
- `scripts/render_week.sh`
- `scripts/render_latest_week.sh`


### scripts/render_latest_week.sh

Convenience wrapper to render the latest week from the configured master doc (same defaults as `render_week.sh latest`).

```bash
scripts/render_latest_week.sh
```

Note:
- This wrapper will **cd to repo root** and **activate `.venv` (if present)**. If you see errors like `ModuleNotFoundError: No module named 'requests'`, it usually means you ran with the system Python without installing deps; fix by creating `.venv` and `pip install -r requirements.txt`.

---

## Output structure

```
wechat_images/
├─ NYU_Weekly/
│  ├─ 00_资料来源.png                # if --top-n > 0
│  ├─ 01_<title>.png
│  ├─ 02_<title>.png
│  └─ ...
├─ UCD_Weekly/
│  ├─ 01_<title>.png                 # left bar alternates blue/yellow
│  └─ ...
└─ EDIN_Weekly/
   └─ ...
```

---

## Tips 

- **Heading 1**: Ensure each news item in the weekly doc begins with Heading 1; otherwise parsing will skip it.
- **Images**: If a cover image is missing in the doc and the source page has no usable meta image, the item is rendered without a cover. Use `--no-images` to speed up rendering if images are not needed.
- **Authentication**: The script now handles expired or revoked tokens automatically. It will prompt you to re-authorize in your browser if `token.pickle` is no longer valid.
- **Date Matching**: When using `render_week.sh exact`, the script first tries an exact string match and then falls back to a logical date range comparison, allowing it to match `2025.11.16 - 11.22` even if you type `2025.11.16 - 2025.11.22`.
- **Cleanup**: Temporary files used for the "Sources" page are automatically cleaned up from the system temp directory.