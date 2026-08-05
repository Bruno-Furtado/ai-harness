#!/usr/bin/env bash
set -euo pipefail

# Reads a hook payload and blocks obvious attempts to access secret files.
# Adapters may pass tool input as JSON on stdin.
payload=$(cat)

if printf '%s' "$payload" | grep -Eiq '(^|[[:space:]/"])\.env($|[.[:space:]/"])|credentials|secrets|\.pem($|[.[:space:]/"])|\.key($|[.[:space:]/"])'; then
  printf '%s\n' 'Blocked: the requested input references a protected secret file.' >&2
  exit 2
fi

exit 0
