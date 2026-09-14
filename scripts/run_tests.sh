#!/bin/bash
# Run the SkillPilot pytest suite (Phase 4–8 API coverage).
# Forces a SQLite test DB so the suite never touches the real PostgreSQL.
set -e
export DATABASE_URL="sqlite:///:memory:"
export SECRET_KEY="${SECRET_KEY:-test-secret-key}"
unset LABOUR_MARKET_SYNC_INTERVAL_HOURS
unset XAPI_LRS_ENDPOINT
exec python -m pytest "$@"
