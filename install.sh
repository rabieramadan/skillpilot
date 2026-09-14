#!/usr/bin/env bash
# ===========================================================================
#  SkillPilot - one-time installer (Linux / macOS)
#
#  Creates a virtual environment, installs dependencies, checks the database
#  connection, creates the schema and seeds the initial accounts.
#
#  Run this once. Afterwards use ./start.sh
# ===========================================================================
set -euo pipefail
cd "$(dirname "$0")"

echo
echo "============================================================"
echo "  SkillPilot installer"
echo "============================================================"
echo

echo "[1/5] Checking Python..."
PYTHON="${PYTHON:-python3}"
if ! command -v "$PYTHON" >/dev/null 2>&1; then
    echo "  ERROR: $PYTHON not found. Install Python 3.11 or newer." >&2
    exit 1
fi
if ! "$PYTHON" -c 'import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)'; then
    echo "  ERROR: Python 3.11 or newer is required (found $("$PYTHON" --version))." >&2
    exit 1
fi
echo "      Found $("$PYTHON" --version)"

echo "[2/5] Creating virtual environment in .venv ..."
if [ -x ".venv/bin/python" ]; then
    echo "      Already exists, reusing it."
else
    "$PYTHON" -m venv .venv
fi
PY=.venv/bin/python

echo "[3/5] Installing dependencies (needs internet, takes 2-5 minutes)..."
"$PY" -m pip install --upgrade pip --quiet
"$PY" -m pip install -r requirements.txt --quiet
echo "      Done."

echo "[4/5] Checking configuration and database..."
if [ ! -f config.yaml ]; then
    if [ -f config.example.yaml ]; then
        cp config.example.yaml config.yaml
        chmod 600 config.yaml
        echo "      Created config.yaml from the example. Add your API keys to"
        echo "      its api_keys: block before the AI features will work."
    else
        echo "  ERROR: neither config.yaml nor config.example.yaml is present." >&2
        exit 1
    fi
fi
chmod 600 config.yaml 2>/dev/null || true
if [ ! -f .env ]; then
    echo "  ERROR: .env is missing. Copy .env.example to .env and fill it in." >&2
    exit 1
fi
chmod 600 .env 2>/dev/null || true
"$PY" check_install.py

echo "[5/5] Creating any missing accounts..."
# Safe on an existing system: accounts that already exist are left alone,
# passwords included.
"$PY" run_seed_users.py || echo "  WARNING: seeding failed; create an administrator manually."

chmod +x start.sh 2>/dev/null || true

cat <<'MSG'

============================================================
  Installation complete.

  Start the server with:  ./start.sh
  Then open:              http://localhost:5000

  Sign in as  admin / admin123  and change that password
  immediately under Profile.
============================================================

MSG
