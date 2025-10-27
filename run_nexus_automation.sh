#!/opt/homebrew/bin/bash
set -euo pipefail

# Absolute paths (per your preference)
PROJECT_DIR="/Users/inwataru/All_My_Projects/NEXUS"
PYTHON_BIN="/Users/inwataru/All_My_Projects/NEXUS/venv/bin/python"

# Optional: allow overriding the delay in seconds via first arg; default 3600 (1 hour)
DELAY_SECS=${1:-3600}

ts() { date '+[%Y-%m-%d %H:%M:%S]'; }

echo "$(ts) Starting delayed run. Will sleep for ${DELAY_SECS}s..."
sleep "${DELAY_SECS}"

cd "${PROJECT_DIR}"

echo "$(ts) Running: python -m news_bot.main_orchestrator (auto input: 5)"
printf '5\n' | "${PYTHON_BIN}" -m news_bot.main_orchestrator

echo "$(ts) First step completed. Running: python -m news_bot.processing.coordinator (auto input: 5)"
printf '5\n' | "${PYTHON_BIN}" -m news_bot.processing.coordinator

echo "$(ts) All steps completed."


