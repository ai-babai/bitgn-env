#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$SCRIPT_DIR/codex-agent-sandbox"
source "$SCRIPT_DIR/scripts/load-omniroute-key.sh"
RUNLOG_HOME_DEFAULT="${RUNLOG_HOME:-$HOME/runlog-registry}"

MODEL="${CODEX_MODEL:-gpt-5.3-codex}"
TIMEOUT_SEC="${CODEX_TIMEOUT_SEC:-240}"
BITGN_API_KEY_FILE="${BITGN_API_KEY_FILE:-$HOME/.bitgn/bitgn-api-key}"

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

if ! bitgn_prepare_codex_backend; then
  exit 1
fi

if [[ "$MODE" == "solve" || "$MODE" == "full-step" || "$MODE" == "autopilot" ]]; then
  if ! bitgn_prepare_codex_auth; then
    exit 1
  fi
fi

if [[ -z "${BITGN_API_KEY:-}" && -f "$BITGN_API_KEY_FILE" ]]; then
  BITGN_API_KEY="$(tr -d '\r\n' < "$BITGN_API_KEY_FILE")"
fi

cd "$APP_DIR"

if [[ -n "${OMNIROUTE_API_KEY:-}" ]]; then
  RUNLOG_HOME="$RUNLOG_HOME_DEFAULT" PYTHONPATH="$SCRIPT_DIR" OMNIROUTE_API_KEY="$OMNIROUTE_API_KEY" CODEX_MODEL="$MODEL" CODEX_TIMEOUT_SEC="$TIMEOUT_SEC" CODEX_PROFILE="${CODEX_PROFILE:-}" CODEX_BACKEND="${CODEX_BACKEND:-omniroute}" BITGN_API_KEY="${BITGN_API_KEY:-}" BITGN_RUN_NAME="${BITGN_RUN_NAME:-}" uv run python evolve.py "$MODE" "$@"
else
  RUNLOG_HOME="$RUNLOG_HOME_DEFAULT" PYTHONPATH="$SCRIPT_DIR" CODEX_MODEL="$MODEL" CODEX_TIMEOUT_SEC="$TIMEOUT_SEC" CODEX_PROFILE="${CODEX_PROFILE:-}" CODEX_BACKEND="${CODEX_BACKEND:-omniroute}" BITGN_API_KEY="${BITGN_API_KEY:-}" BITGN_RUN_NAME="${BITGN_RUN_NAME:-}" OMNIROUTE_API_KEY="${OMNIROUTE_API_KEY:-}" uv run python evolve.py "$MODE" "$@"
fi
