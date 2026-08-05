#!/usr/bin/env bash
set -euo pipefail

payload=$(cat)

# Parse only the fields required by this hook. Never log the payload.
if [[ -z "$payload" ]]; then
  exit 0
fi

exit 0
