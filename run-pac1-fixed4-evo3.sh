#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNNER="$SCRIPT_DIR/run-codex-evolve.sh"

TASKS=(t03 t22 t23 t25)

"$RUNNER" full-step --env pac1 --hypothesis "pac1 fixed-4 step1" "${TASKS[@]}"
"$RUNNER" full-step --env pac1 --hypothesis "pac1 fixed-4 step2" "${TASKS[@]}"
"$RUNNER" full-step --env pac1 --hypothesis "pac1 fixed-4 step3" "${TASKS[@]}"
