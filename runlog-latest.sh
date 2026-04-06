#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOME_DIR="${RUNLOG_HOME:-/Users/skif/develop/runlog-registry}"

PYTHONPATH="$ROOT_DIR" python3 -m runlog_core.cli latest --home "$HOME_DIR"
