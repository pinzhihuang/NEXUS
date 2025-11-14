#!/usr/bin/env bash
set -euo pipefail

# 固定你的总表链接
MASTER_DOC="https://docs.google.com/document/d/1scFGNSGj0pLEDZWLrGNeqsTiHrkmOUGYd-Yus3LkjYU/edit?tab=t.0"

# 可选：这些有默认值，也可以改
OUT_DIR="wechat_images"
PAGE_WIDTH=540
DEVICE_SCALE=4
TOP_N=10

echo "[*] Rendering LATEST week from MASTER_DOC=$MASTER_DOC"
python3 scripts/gdoc_master_latest_to_images.py \
  --master-doc "$MASTER_DOC" \
  --out "$OUT_DIR" \
  --page-width "$PAGE_WIDTH" \
  --device-scale "$DEVICE_SCALE" \
  --top-n "$TOP_N"