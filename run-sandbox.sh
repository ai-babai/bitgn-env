#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$SCRIPT_DIR/sample-agents/sandbox-py"

KEY_FILE="${BITGN_OMNIROUTE_KEY_FILE:-/Users/skif/obsidian/skif-os/81-secrets-ai/homelab-omniroute/dev-key.md}"
BASE_URL="${OPENAI_BASE_URL:-https://omni.mipopkov.com/v1}"
MODEL="${MODEL_ID:-codex/gpt-5.3-codex-high}"

SYNC=0
ALL=0
TASKS=()

while (($#)); do
  case "$1" in
    --sync)
      SYNC=1
      ;;
    --all)
      ALL=1
      ;;
    -h|--help)
      cat <<'EOF'
Usage:
  ./run-sandbox.sh [--sync] [--all] [task-id ...]

Examples:
  ./run-sandbox.sh            # smoke (t01 t02)
  ./run-sandbox.sh t01        # single task
  ./run-sandbox.sh t03 t04    # selected tasks
  ./run-sandbox.sh --all      # full benchmark
  ./run-sandbox.sh --sync t01 # force dependency sync first

Optional env overrides:
  BITGN_OMNIROUTE_KEY_FILE
  OPENAI_BASE_URL
  MODEL_ID
  OPENAI_API_KEY
EOF
      exit 0
      ;;
    *)
      TASKS+=("$1")
      ;;
  esac
  shift
done

if [[ -z "${OPENAI_API_KEY:-}" ]]; then
  if [[ ! -f "$KEY_FILE" ]]; then
    echo "ERROR: key file not found: $KEY_FILE" >&2
    exit 1
  fi
  OPENAI_API_KEY="$(tr -d '\r\n' < "$KEY_FILE")"
fi

if [[ -z "$OPENAI_API_KEY" ]]; then
  echo "ERROR: OPENAI_API_KEY is empty" >&2
  exit 1
fi

cd "$APP_DIR"

if [[ $SYNC -eq 1 || ! -d ".venv" ]]; then
  uv python pin 3.13 >/dev/null
  uv sync --python 3.13
fi

if [[ $ALL -eq 0 && ${#TASKS[@]} -eq 0 ]]; then
  TASKS=(t01 t02)
fi

CMD=(uv run python -u main.py)
if [[ $ALL -eq 0 ]]; then
  CMD+=("${TASKS[@]}")
fi

OPENAI_BASE_URL="$BASE_URL" MODEL_ID="$MODEL" OPENAI_API_KEY="$OPENAI_API_KEY" "${CMD[@]}"
