#!/bin/sh
set -e

export BACKEND_URL="http://127.0.0.1:${PORT:-8000}"

cd /app && python -m bot.main &
cd /app/backend && exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
