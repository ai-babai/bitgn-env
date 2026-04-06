#!/usr/bin/env bash

if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
  export PATH="$HOME/.local/bin:$PATH"
fi

bitgn_require_omniroute_key() {
  if [[ -n "${OMNIROUTE_API_KEY:-}" ]]; then
    export OMNIROUTE_API_KEY
    return 0
  fi

  local key_file="${BITGN_OMNIROUTE_KEY_FILE:-$HOME/.codex/omniroute-api-key}"

  if [[ ! -f "$key_file" ]]; then
    echo "ERROR: OMNIROUTE_API_KEY is not set and key file not found: $key_file" >&2
    echo "Set OMNIROUTE_API_KEY or provide BITGN_OMNIROUTE_KEY_FILE" >&2
    return 1
  fi

  OMNIROUTE_API_KEY="$(tr -d '\r\n' < "$key_file")"
  if [[ -z "$OMNIROUTE_API_KEY" ]]; then
    echo "ERROR: OMNIROUTE_API_KEY is empty (source: $key_file)" >&2
    return 1
  fi

  export OMNIROUTE_API_KEY
}
