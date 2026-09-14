#!/usr/bin/env bash
# ===========================================================================
#  SkillPilot - start the server (Linux / macOS, production)
# ===========================================================================
set -euo pipefail
cd "$(dirname "$0")"

PORT="${PORT:-5000}"
THREADS="${THREADS:-8}"
export FLASK_ENV=production

if [ ! -x ".venv/bin/python" ]; then
    echo "  ERROR: not installed yet. Run ./install.sh first." >&2
    exit 1
fi

echo
echo "============================================================"
echo "  SkillPilot starting on http://0.0.0.0:${PORT}"
echo "  Local access:  http://localhost:${PORT}"
echo "  Press Ctrl+C to stop."
echo "============================================================"
echo

exec .venv/bin/python serve.py --host 0.0.0.0 --port "$PORT" --threads "$THREADS"
