#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$SCRIPT_DIR/codex-agent-native"

KEY_FILE="${BITGN_OMNIROUTE_KEY_FILE:-/Users/skif/obsidian/skif-os/81-secrets-ai/homelab-omniroute/dev-key.md}"
BASE_URL="${OPENAI_BASE_URL:-https://omni.mipopkov.com/v1}"
MODEL="${CODEX_MODEL:-gpt-5.3-codex}"
TIMEOUT_SEC="${CODEX_TIMEOUT_SEC:-240}"
ENV_ID="sandbox"
PARALLELISM=""

ARGS=("$@")
TASKS=()
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
    --parallelism=*)
      PARALLELISM="${arg#*=}"
      ;;
    --parallelism|-p)
      if [[ $((i+1)) -lt ${#ARGS[@]} ]]; then
        PARALLELISM="${ARGS[$((i+1))]}"
        i=$((i+1))
      fi
      ;;
    --*)
      ;;
    *)
      TASKS+=("$arg")
      ;;
  esac
  i=$((i+1))
done

if [[ ${#TASKS[@]} -eq 0 ]]; then
  echo "Usage: ./run-codex-native.sh [--env sandbox|pac1] [-p|--parallelism N] <task-id> [task-id2 ...]" >&2
  exit 1
fi

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

if [[ "$ENV_ID" == "pac1" ]]; then
  export BENCHMARK_ID="${BENCHMARK_ID:-bitgn/pac1-dev}"
  export AGENT_ENV="pac1"
else
  export BENCHMARK_ID="${BENCHMARK_ID:-bitgn/sandbox}"
  export AGENT_ENV="sandbox"
fi

cd "$APP_DIR"

RUN_ARGS=("${TASKS[@]}")
if [[ -n "$PARALLELISM" ]]; then
  RUN_ARGS+=("--parallelism" "$PARALLELISM")
fi

OPENAI_BASE_URL="$BASE_URL" OPENAI_API_KEY="$OPENAI_API_KEY" CODEX_MODEL="$MODEL" CODEX_TIMEOUT_SEC="$TIMEOUT_SEC" uv run python runner.py "${RUN_ARGS[@]}"
