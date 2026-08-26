#!/usr/bin/env bash
# Stops the background server and removes the virtual environment and cache.
# Usage: ./uninstall.sh [--keep-env]   (--keep-env preserves .venv and .env)
set -euo pipefail

KEEP_ENV=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --keep-env) KEEP_ENV=true; shift ;;
    *) echo "Unknown option: $1"; echo "Usage: $0 [--keep-env]"; exit 1 ;;
  esac
done

# ── stop server ───────────────────────────────────────────────────────────────
if [[ -f .server.pid ]]; then
  PID=$(cat .server.pid)
  if kill -0 "$PID" 2>/dev/null; then
    echo "Stopping API server (PID $PID)..."
    kill "$PID"; sleep 1
    echo "Server stopped."
  else
    echo "API server process $PID was not running."
  fi
  rm -f .server.pid
else
  echo "No .server.pid found — server may not have been started by install.sh."
fi

# ── stop Streamlit ────────────────────────────────────────────────────────────
if [[ -f .streamlit.pid ]]; then
  SPID=$(cat .streamlit.pid)
  if kill -0 "$SPID" 2>/dev/null; then
    echo "Stopping Streamlit UI (PID $SPID)..."
    kill "$SPID"; sleep 1
    echo "Streamlit stopped."
  else
    echo "Streamlit process $SPID was not running."
  fi
  rm -f .streamlit.pid
fi

rm -f server.log streamlit.log

# ── clean up generated files ──────────────────────────────────────────────────
rm -rf .cache/

if [[ "$KEEP_ENV" == false ]]; then
  rm -rf .venv/
  echo "Removed .venv"
  echo ""
  echo "Note: .env was kept (contains your API key). Remove it manually if needed:"
  echo "  rm .env"
else
  echo "Kept .venv and .env (--keep-env)"
fi

echo "Done."
