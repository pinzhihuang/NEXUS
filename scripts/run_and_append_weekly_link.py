#!/usr/bin/env python3
"""
Run the two automation steps and append the generated Google Doc link
to the weekly汇总 Google Doc.

Format to append:
  1) First line: "<NEWS_START_DATE> - <NEWS_START_DATE + RECENCY_THRESHOLD_DAYS - 1>"
  2) Second line: "<newly generated Google Doc URL>"
"""
import sys
# Ensure project root is on sys.path so `news_bot` can be imported when running this script directly
PROJECT_DIR = "/Users/inwataru/All_My_Projects/NEXUS"
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)
import os
import re
import subprocess
from datetime import timedelta
from typing import Optional

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Reuse existing config and OAuth from the project
from news_bot.core import config
from news_bot.reporting.google_docs_exporter import _get_credentials

PYTHON_BIN = "/Users/inwataru/All_My_Projects/NEXUS/venv/bin/python"

# Target weekly汇总 Google Doc (provided by user)
AGGREGATE_DOC_ID = "1scFGNSGj0pLEDZWLrGNeqsTiHrkmOUGYd-Yus3LkjYU"

# School selection fed to existing interactive modules
DEFAULT_SCHOOL_ID_INPUT = "1\n"

def _run_module(module_name: str, input_text: Optional[str], capture_output: bool) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    cwd = PROJECT_DIR
    return subprocess.run(
        [PYTHON_BIN, "-m", module_name],
        input=input_text if input_text is not None else None,
        text=True,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE if capture_output else None,
        stderr=subprocess.STDOUT if capture_output else None,
        check=True,
    )


def _parse_gdoc_url(output_text: str) -> Optional[str]:
    """
    Extract the last Google Doc URL printed by the coordinator, e.g.:
      '导出成功: https://docs.google.com/document/d/<ID>/edit'
    """
    if not output_text:
        return None
    pattern = re.compile(r"https://docs\.google\.com/document/d/[A-Za-z0-9_\-]+/edit[^\s]*")
    matches = pattern.findall(output_text)
    return matches[-1] if matches else None
def _compute_label_line() -> str:
    """
    Build the first line "<start_date> - <end_date>" from .env settings,
    following the same date-range logic used by the app.
    """
    # If NEWS_START_DATE is set in .env, config.get_news_date_range() returns:
    #   (start, start + RECENCY_THRESHOLD_DAYS - 1)
    start_date, end_date = config.get_news_date_range()
    return f"{start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')}"


def _append_lines_to_aggregate_doc(doc_id: str, text_to_append: str) -> None:
    creds = _get_credentials()
    if not creds:
        raise RuntimeError("Failed to obtain Google OAuth credentials; cannot update the summary Google Doc.")

    service = build("docs", "v1", credentials=creds)
    # Get current end index to append at the end
    doc = service.documents().get(documentId=doc_id).execute()
    content = doc.get("body", {}).get("content", [])
    if not content:
        # Minimal doc: first insert location is index=1
        end_index = 1
    else:
        end_index = content[-1].get("endIndex", 1)
        if not isinstance(end_index, int):
            end_index = 1

    requests = [
        {
            "insertText": {
                "location": {"index": max(1, end_index - 1)},
                "text": text_to_append,
            }
        }
    ]

    try:
        service.documents().batchUpdate(documentId=doc_id, body={"requests": requests}).execute()
    except HttpError as e:
        raise RuntimeError(f"Google Docs API error while appending to summary doc: {e}")


def main() -> None:
    print("[run_and_append_weekly_link] Running Step 1: news_bot.main_orchestrator")
    _run_module("news_bot.main_orchestrator", input_text=DEFAULT_SCHOOL_ID_INPUT, capture_output=False)

    print("[run_and_append_weekly_link] Running Step 2: news_bot.processing.coordinator and capturing output")
    proc = _run_module("news_bot.processing.coordinator", input_text=DEFAULT_SCHOOL_ID_INPUT, capture_output=True)
    coordinator_output = proc.stdout or ""

    gdoc_url = _parse_gdoc_url(coordinator_output)
    if not gdoc_url:
        # Fallback: if TARGET_GOOGLE_DOC_ID is configured, synthesize URL
        if config.TARGET_GOOGLE_DOC_ID:
            gdoc_url = f"https://docs.google.com/document/d/{config.TARGET_GOOGLE_DOC_ID}/edit"
            print("[run_and_append_weekly_link] Coordinator output did not include a URL; "
                  "falling back to TARGET_GOOGLE_DOC_ID from config.")
        else:
            print(coordinator_output)
            raise RuntimeError("Could not find Google Doc URL in coordinator output and no TARGET_GOOGLE_DOC_ID set.")

    label_line = _compute_label_line()
    text_block = f"{label_line}\n{gdoc_url}\n\n"
    print(f"[run_and_append_weekly_link] Appending to weekly summary doc ({AGGREGATE_DOC_ID}):")
    print(text_block)

    _append_lines_to_aggregate_doc(AGGREGATE_DOC_ID, text_block)
    print("[run_and_append_weekly_link] Successfully appended to weekly summary Google Doc.")


if __name__ == "__main__":
    main()

