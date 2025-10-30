#!/usr/bin/env bash
set -euo pipefail

# 1) 切到仓库根
cd "$(dirname "$0")/.."

# 2) 自动激活虚拟环境（若存在）
if [[ -d ".venv" ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

# 3) 自动设置 PYTHONPATH 指向仓库根（确保能 import news_bot/*）
export PYTHONPATH="${PYTHONPATH:-$(pwd)}"

# 4) 默认参数
OUT_DIR="${OUT_DIR:-wechat_images}"
PAGE_WIDTH="${PAGE_WIDTH:-540}"
DEVICE_SCALE="${DEVICE_SCALE:-4}"
TOP_N="${TOP_N:-10}"
BRAND_COLOR="${BRAND_COLOR:-}"

# 5) 取入参
DOC_ARG="${1:-}"
if [[ -z "${DOC_ARG}" ]]; then
  read -rp "请输入子文档链接或 docId: " DOC_ARG
fi
if [[ -n "${2:-}" ]]; then
  BRAND_COLOR="$2"
fi

echo "[*] Rendering single doc: ${DOC_ARG}"
if [[ -n "${BRAND_COLOR}" ]]; then
  echo "[*] Override brand_color=${BRAND_COLOR}"
fi

# 6) 调用单文档渲染脚本（仍走 scripts/gdoc_to_wechat_images.py）
python3 scripts/gdoc_to_wechat_images.py \
  --doc "${DOC_ARG}" \
  --out "${OUT_DIR}" \
  --page-width "${PAGE_WIDTH}" \
  --device-scale "${DEVICE_SCALE}" \
  --top-n "${TOP_N}" \
  ${BRAND_COLOR:+--brand-color "${BRAND_COLOR}"}
