#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$SCRIPT_DIR/codex-agent-sandbox"

KEY_FILE="${BITGN_OMNIROUTE_KEY_FILE:-/Users/skif/obsidian/skif-os/81-secrets-ai/homelab-omniroute/dev-key.md}"
BASE_URL="${OPENAI_BASE_URL:-https://omni.mipopkov.com/v1}"
MODEL="${CODEX_MODEL:-gpt-5.3-codex}"
TIMEOUT_SEC="${CODEX_TIMEOUT_SEC:-240}"

if [[ $# -lt 1 ]]; then
  echo "Usage: ./run-codex-evolve.sh <solve|analyze|propose-prompts|propose-code|apply-prompts|full-step|autopilot> [args...]" >&2
  exit 1
fi

MODE="$1"
shift

ENV_ID="sandbox"
ARGS=("$@")
i=0
while [[ $i -lt ${#ARGS[@]} ]]; do
  arg="${ARGS[$i]}"
  case "$arg" in
    --env=pac1)
      ENV_ID="pac1"
      ;;
    --env=sandbox)
      ENV_ID="sandbox"
      ;;
    --env)
      if [[ $((i+1)) -lt ${#ARGS[@]} ]]; then
        ENV_ID="${ARGS[$((i+1))]}"
        i=$((i+1))
      fi
      ;;
  esac
  i=$((i+1))
done

if [[ "$ENV_ID" == "pac1" ]]; then
  export BENCHMARK_ID="${BENCHMARK_ID:-bitgn/pac1-dev}"
  export AGENT_ENV="pac1"
else
  export BENCHMARK_ID="${BENCHMARK_ID:-bitgn/sandbox}"
  export AGENT_ENV="sandbox"
fi

if [[ "$MODE" == "solve" || "$MODE" == "full-step" || "$MODE" == "autopilot" ]]; then
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
  export OPENAI_API_KEY
fi

cd "$APP_DIR"

PYTHONPATH="$SCRIPT_DIR" OPENAI_BASE_URL="$BASE_URL" CODEX_MODEL="$MODEL" CODEX_TIMEOUT_SEC="$TIMEOUT_SEC" uv run python evolve.py "$MODE" "$@"
