#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

LOG_LEVEL="${1:-${LOG_LEVEL:-DEBUG}}"
export LOG_LEVEL
UVICORN_HOST="${UVICORN_HOST:-0.0.0.0}"
UVICORN_PORT="${UVICORN_PORT:-8000}"
UVICORN_RELOAD="${UVICORN_RELOAD:-0}"

uvicorn_args=(
    app.main:app
    --host "$UVICORN_HOST"
    --port "$UVICORN_PORT"
)

case "${UVICORN_RELOAD,,}" in
    1|true|yes|on)
        uvicorn_args+=(--reload)
        ;;
esac

mask_database_url() {
    local value="$1"
    if [[ "$value" =~ ^([^:]+://[^:]+:)[^@]+(@.*)$ ]]; then
        echo "${BASH_REMATCH[1]}***${BASH_REMATCH[2]}"
        return
    fi
    echo "$value"
}

resolve_database_url() {
    python -c "
import sys
sys.path.insert(0, '.')
from app.config import ENV_FILE_PATH, get_settings
get_settings.cache_clear()
print(ENV_FILE_PATH)
print('1' if ENV_FILE_PATH.exists() else '0')
print(get_settings().DATABASE_URL)
"
}

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

source .venv/bin/activate
.venv/bin/pip install -q -r requirements.txt

mapfile -t runtime_db_config < <(resolve_database_url)
ENV_FILE_PATH="${runtime_db_config[0]:-unknown}"
ENV_FILE_EXISTS="${runtime_db_config[1]:-0}"
RESOLVED_DATABASE_URL="${runtime_db_config[2]:-sqlite+aiosqlite:///./db.sqlite3}"
export DATABASE_URL="$RESOLVED_DATABASE_URL"
echo "Config env file: ${ENV_FILE_PATH} (exists=${ENV_FILE_EXISTS})"
echo "Runtime DATABASE_URL=$(mask_database_url "$RESOLVED_DATABASE_URL")"
echo "Initializing database..."
python -c "
import asyncio, sys; sys.path.insert(0, '.')
from app.config import get_settings; get_settings.cache_clear()
import app.models
from app.database import init_db
asyncio.run(init_db())
print('Database initialized.')
"

echo "Starting backend on http://${UVICORN_HOST}:${UVICORN_PORT} ... (LOG_LEVEL=$LOG_LEVEL, RELOAD=${UVICORN_RELOAD})"
exec uvicorn "${uvicorn_args[@]}"
