#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ -d ".venv" ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

MASTER_DOC="https://docs.google.com/document/d/1scFGNSGj0pLEDZWLrGNeqsTiHrkmOUGYd-Yus3LkjYU/edit?tab=t.0"

OUT_DIR="wechat_images"
PAGE_WIDTH=540
DEVICE_SCALE=4
TOP_N=10

MODE="${1:-}"        # latest | exact
ARG="${2:-}"         # 当 MODE=exact 时，这里是周标题

if [[ -z "$MODE" ]]; then
  echo "选择模式：[1] 最新一周   [2] 指定周（输入标题）"
  read -rp "输入 1 或 2: " choice
  if [[ "$choice" == "1" ]]; then
    MODE="latest"
  else
    MODE="exact"
  fi
fi

if [[ "$MODE" == "latest" ]]; then
  echo "[*] Rendering LATEST week..."
  python3 script/gdoc_master_latest_to_images.py \
    --master-doc "$MASTER_DOC" \
    --out "$OUT_DIR" \
    --page-width "$PAGE_WIDTH" \
    --device-scale "$DEVICE_SCALE" \
    --top-n "$TOP_N"
elif [[ "$MODE" == "exact" ]]; then
  if [[ -z "$ARG" ]]; then
    read -rp "请输入周标题（例：2025.10.12 - 10.18）: " ARG
  fi
  echo "[*] Rendering WEEK: $ARG"
  python3 script/gdoc_master_latest_to_images.py \
    --master-doc "$MASTER_DOC" \
    --out "$OUT_DIR" \
    --page-width "$PAGE_WIDTH" \
    --device-scale "$DEVICE_SCALE" \
    --top-n "$TOP_N" \
    --week-title "$ARG"
else
  echo "不支持的模式：$MODE（可用：latest / exact）"
  exit 1
fi
