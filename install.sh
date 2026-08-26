#!/usr/bin/env bash
# Usage:
#   ./install.sh --api-key YOUR_GEMINI_KEY
#   ./install.sh --api-key YOUR_GEMINI_KEY --port 8080
set -euo pipefail

# ── defaults ────────────────────────────────────────────────────────────────
PORT=8000
API_KEY=""

# ── argument parsing ─────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --api-key)
      if [[ -z "${2:-}" ]]; then
        echo "Error: --api-key requires a value."; exit 1
      fi
      API_KEY="$2"; shift 2 ;;
    --port)
      if [[ -z "${2:-}" ]]; then
        echo "Error: --port requires a value."; exit 1
      fi
      PORT="$2"; shift 2 ;;
    *) echo "Unknown option: $1"; echo "Usage: $0 --api-key KEY [--port PORT]"; exit 1 ;;
  esac
done

if [[ -z "$API_KEY" ]]; then
  echo "Error: --api-key is required."
  echo "Get a free key at https://aistudio.google.com/apikey"
  echo "Usage: $0 --api-key YOUR_GEMINI_KEY"
  exit 1
fi

# ── detect python ────────────────────────────────────────────────────────────
if command -v python3 &>/dev/null; then
  PYTHON=python3
elif command -v python &>/dev/null; then
  PYTHON=python
else
  echo "Error: Python not found. Install Python 3.9+ and retry."
  exit 1
fi

PY_MINOR=$($PYTHON -c "import sys; print(sys.version_info.minor)")
PY_MAJOR=$($PYTHON -c "import sys; print(sys.version_info.major)")
if [[ "$PY_MAJOR" -lt 3 || ("$PY_MAJOR" -eq 3 && "$PY_MINOR" -lt 9) ]]; then
  echo "Error: Python 3.9+ required (found $($PYTHON --version))."
  exit 1
fi

echo "Using $($PYTHON --version)"

# ── virtual environment ───────────────────────────────────────────────────────
if [[ ! -d .venv ]]; then
  echo "Creating virtual environment..."
  $PYTHON -m venv .venv
fi

# shellcheck source=/dev/null
source .venv/bin/activate

echo "Installing dependencies..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

# ── environment file ──────────────────────────────────────────────────────────
if [[ ! -f .env ]]; then
  cp .env.example .env
fi

# Replace the key line in-place regardless of whether it was already set
if grep -q "^GEMINI_API_KEY=" .env; then
  sed -i "s|^GEMINI_API_KEY=.*|GEMINI_API_KEY=${API_KEY}|" .env
else
  echo "GEMINI_API_KEY=${API_KEY}" >> .env
fi

# ── start server in background ────────────────────────────────────────────────
# Stop any server we previously started before launching a new one
if [[ -f .server.pid ]]; then
  OLD_PID=$(cat .server.pid)
  if kill -0 "$OLD_PID" 2>/dev/null; then
    echo "Stopping previous server (PID $OLD_PID)..."
    kill "$OLD_PID"
    sleep 1
  fi
  rm -f .server.pid
fi

echo "Starting API server on port $PORT..."
nohup .venv/bin/uvicorn app.api:app --host 127.0.0.1 --port "$PORT" \
  > server.log 2>&1 &
echo $! > .server.pid

# wait up to 10 s for the server to accept connections
for i in $(seq 1 20); do
  if curl -s -o /dev/null "http://127.0.0.1:${PORT}/docs"; then
    break
  fi
  sleep 0.5
done

echo ""
echo "✓ Server running (PID $(cat .server.pid))"
echo "  Swagger UI : http://127.0.0.1:${PORT}/docs"
echo ""

# ── live sample calls ─────────────────────────────────────────────────────────
echo "━━━ Task 1 · Triage sample ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
curl -s -X POST "http://127.0.0.1:${PORT}/triage" \
  -H "Content-Type: application/json" \
  -d '{"subject":"SSO configuration not working for new users","body":"308 people blocked from accessing the platform since this morning. They cannot log in via our corporate SSO provider."}' \
  | python3 -m json.tool
echo ""

echo "━━━ Task 2 · Account brief (ACC-2944) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
curl -s "http://127.0.0.1:${PORT}/account-brief/ACC-2944" \
  | python3 -m json.tool
echo ""

echo "━━━ Next steps ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Run eval harness:"
echo "    .venv/bin/python -m eval.run_eval"
echo ""

# ── start Streamlit in background ─────────────────────────────────────────────
STREAMLIT_PORT=8501
if [[ -f .streamlit.pid ]]; then
  OLD_SPID=$(cat .streamlit.pid)
  if kill -0 "$OLD_SPID" 2>/dev/null; then
    kill "$OLD_SPID"; sleep 1
  fi
  rm -f .streamlit.pid
fi
nohup .venv/bin/streamlit run ui/streamlit_app.py \
  --server.headless true \
  --server.port "$STREAMLIT_PORT" \
  > streamlit.log 2>&1 &
echo $! > .streamlit.pid

# wait up to 8 s for Streamlit to be ready
for i in $(seq 1 16); do
  if curl -s -o /dev/null "http://localhost:${STREAMLIT_PORT}"; then
    break
  fi
  sleep 0.5
done

echo "  ✨ Bonus UI (TAM demo):"
echo "     http://localhost:${STREAMLIT_PORT}"
echo ""
echo "  To stop everything: ./uninstall.sh"
