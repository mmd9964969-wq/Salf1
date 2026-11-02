#!/bin/sh
set -eu

cd /app
export PORT="${PORT:-4173}"
export SALF1_PORT="${SALF1_PORT:-8080}"
export PYTHONUNBUFFERED=1

/opt/salf1-venv/bin/python /app/telegram-worker/main.py &
BOT_PID=$!

node /app/server.js &
WEB_PID=$!

cleanup() {
  kill -TERM "$BOT_PID" "$WEB_PID" 2>/dev/null || true
  wait "$BOT_PID" 2>/dev/null || true
  wait "$WEB_PID" 2>/dev/null || true
}

trap cleanup INT TERM

# A failed web or bot process must fail the whole runtime so Cloudflare can
# restart the container instead of silently leaving half the application up.
while kill -0 "$BOT_PID" 2>/dev/null && kill -0 "$WEB_PID" 2>/dev/null; do
  sleep 2
done

echo "SALF1 child process exited; stopping the remaining process."
cleanup
exit 1
