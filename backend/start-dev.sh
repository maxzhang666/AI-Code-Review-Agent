#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

# Development defaults: enable reload automatically.
export UVICORN_RELOAD=1
export LOG_LEVEL="${LOG_LEVEL:-DEBUG}"

exec ./start.sh "$LOG_LEVEL"
