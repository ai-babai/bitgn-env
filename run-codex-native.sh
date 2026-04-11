#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$SCRIPT_DIR/codex-agent-native"
source "$SCRIPT_DIR/scripts/load-omniroute-key.sh"
RUNLOG_HOME_DEFAULT="${RUNLOG_HOME:-$HOME/runlog-registry}"

MODEL="${CODEX_MODEL:-gpt-5.3-codex}"
TIMEOUT_SEC="${CODEX_TIMEOUT_SEC:-240}"
BITGN_API_KEY_FILE="${BITGN_API_KEY_FILE:-$HOME/.bitgn/bitgn-api-key}"
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
    --env=pac1-prod)
      ENV_ID="pac1-prod"
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
  echo "Usage: ./run-codex-native.sh [--env sandbox|pac1|pac1-prod] [-p|--parallelism N] <task-id> [task-id2 ...]" >&2
  exit 1
fi

if ! bitgn_prepare_codex_auth; then
  exit 1
fi

if [[ -z "${BITGN_API_KEY:-}" && -f "$BITGN_API_KEY_FILE" ]]; then
  BITGN_API_KEY="$(tr -d '\r\n' < "$BITGN_API_KEY_FILE")"
fi

if [[ "$ENV_ID" == "pac1-prod" ]]; then
  export BENCHMARK_ID="${BENCHMARK_ID:-bitgn/pac1-prod}"
  export AGENT_ENV="pac1"
elif [[ "$ENV_ID" == "pac1" ]]; then
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

RUNLOG_HOME="$RUNLOG_HOME_DEFAULT" CODEX_MODEL="$MODEL" CODEX_TIMEOUT_SEC="$TIMEOUT_SEC" CODEX_PROFILE="${CODEX_PROFILE:-}" CODEX_BACKEND="$CODEX_BACKEND" BITGN_API_KEY="${BITGN_API_KEY:-}" BITGN_RUN_NAME="${BITGN_RUN_NAME:-}" OMNIROUTE_API_KEY="${OMNIROUTE_API_KEY:-}" uv run python runner.py "${RUN_ARGS[@]}"
