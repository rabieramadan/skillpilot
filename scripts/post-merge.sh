#!/bin/bash
set -e

# SkillPilot is a Python/Flask app. Database schema is created/extended
# automatically by db.create_all() at app startup (see app/__init__.py),
# so no migration command is needed here.
#
# Python dependencies are declared in pyproject.toml and managed by uv,
# which the Replit env keeps in sync — nothing to install here either.

echo "[post-merge] SkillPilot Python project — running pytest suite as a regression safety net."

# Run the same pytest suite that CI runs on every push/PR. This catches
# regressions immediately after a merge in the local Replit environment.
# Set SKIP_POST_MERGE_TESTS=1 to bypass (e.g. for hotfix merges).
if [ "${SKIP_POST_MERGE_TESTS:-0}" = "1" ]; then
  echo "[post-merge] SKIP_POST_MERGE_TESTS=1 — skipping pytest."
  exit 0
fi

# Skip gracefully if pytest isn't available in this workspace (e.g. dev
# dependencies aren't installed). CI installs pytest from the lockfile,
# so this fallback only affects local Replit merges.
if ! python -c "import pytest" >/dev/null 2>&1; then
  echo "[post-merge] pytest not installed in this environment — skipping local test run."
  echo "[post-merge] CI will still run the full suite on push/PR."
  exit 0
fi

bash "$(dirname "$0")/run_tests.sh"
