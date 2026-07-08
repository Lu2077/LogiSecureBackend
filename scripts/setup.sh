#!/usr/bin/env bash
# ==============================================================================
# LOGISECURE AI - ONE-COMMAND DEV SETUP (Linux / macOS / Git Bash)
# Usage (from anywhere):   ./scripts/setup.sh
# Creates backend/.venv, installs dependencies, prepares backend/.env
# ==============================================================================
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND="$REPO_ROOT/backend"

echo ""
echo "=== LogiSecure AI :: Backend Dev Setup ==="

# 1. Verify Python
PYTHON_BIN="$(command -v python3 || command -v python || true)"
if [[ -z "$PYTHON_BIN" ]]; then
    echo "Python not found. Install Python 3.10+ and retry." >&2
    exit 1
fi
echo "[1/4] Using $("$PYTHON_BIN" --version)"

# 2. Virtual environment
if [[ ! -d "$BACKEND/.venv" ]]; then
    echo "[2/4] Creating virtual environment at backend/.venv ..."
    "$PYTHON_BIN" -m venv "$BACKEND/.venv"
else
    echo "[2/4] Reusing existing backend/.venv"
fi

# Windows (Git Bash) venvs use Scripts/, POSIX venvs use bin/
VENV_PY="$BACKEND/.venv/bin/python"
[[ -x "$VENV_PY" ]] || VENV_PY="$BACKEND/.venv/Scripts/python.exe"

# 3. Dependencies
echo "[3/4] Installing backend dependencies ..."
"$VENV_PY" -m pip install --upgrade pip --quiet
"$VENV_PY" -m pip install -r "$BACKEND/requirements.txt"

# 4. Environment file
if [[ ! -f "$BACKEND/.env" ]]; then
    cp "$REPO_ROOT/.env.example" "$BACKEND/.env"
    echo "[4/4] Created backend/.env from .env.example (fill in your API keys)"
else
    echo "[4/4] backend/.env already exists - left untouched"
fi

echo ""
echo "Setup complete! Run the API with:"
echo "    cd backend && source .venv/bin/activate && uvicorn main:app --reload"
echo ""
echo "Or skip all of the above and use Docker:"
echo "    docker compose -f deploy/docker-compose.yml up --build"
echo ""
echo "API:    http://localhost:8000"
echo "Docs:   http://localhost:8000/docs"
echo "Health: http://localhost:8000/health"
