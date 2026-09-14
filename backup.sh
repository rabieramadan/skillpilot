#!/usr/bin/env bash
# ===========================================================================
#  SkillPilot - back up everything that cannot be reinstalled
#
#  Run this before upgrading, and on a schedule. It captures the three things
#  the application code cannot recreate:
#
#    1. the PostgreSQL database  - users, courses, enrolments, results
#    2. uploaded and generated files - uploads/, certificates/, course_files/
#    3. configuration - config.yaml (API keys, model catalogue) and .env
#
#  Usage:  ./backup.sh [destination-directory]
#          default destination: ./backups
# ===========================================================================
set -euo pipefail
cd "$(dirname "$0")"

DEST="${1:-backups}"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="$DEST/skillpilot-$STAMP"
mkdir -p "$OUT"

echo
echo "Backing up to $OUT"
echo

# --- 1. Database -----------------------------------------------------------
DB_URL="$(grep -E '^DATABASE_URL=' .env 2>/dev/null | cut -d= -f2- || true)"
if [ -n "$DB_URL" ] && command -v pg_dump >/dev/null 2>&1; then
    echo "  database ..."
    if pg_dump "$DB_URL" > "$OUT/database.sql" 2>"$OUT/database.err"; then
        rm -f "$OUT/database.err"
        echo "      $(du -h "$OUT/database.sql" | cut -f1) written"
    else
        echo "      FAILED - see $OUT/database.err" >&2
        echo "      Back the database up by hand before upgrading." >&2
    fi
else
    echo "  database ... SKIPPED (pg_dump not found, or DATABASE_URL unset)" >&2
    echo "      Back the database up by hand before upgrading." >&2
fi

# --- 2. Files the application wrote ---------------------------------------
for dir in uploads certificates certificates_issued course_files exam_data exports; do
    if [ -d "$dir" ] && [ -n "$(ls -A "$dir" 2>/dev/null)" ]; then
        echo "  $dir/ ..."
        cp -a "$dir" "$OUT/"
    fi
done

# Data the application keeps in JSON files beside the code.
mkdir -p "$OUT/json"
copied=0
for f in *.json; do
    [ -e "$f" ] || continue
    case "$f" in package.json|package-lock.json) continue ;; esac
    cp -a "$f" "$OUT/json/"
    copied=$((copied + 1))
done
[ "$copied" -gt 0 ] && echo "  $copied JSON data file(s) ..." || rmdir "$OUT/json"

# --- 3. Configuration ------------------------------------------------------
echo "  configuration ..."
for f in config.yaml .env .env.server; do
    [ -f "$f" ] && cp -a "$f" "$OUT/"
done
chmod -R go-rwx "$OUT" 2>/dev/null || true

cat > "$OUT/RESTORE.txt" <<TXT
SkillPilot backup taken $STAMP

To restore:

  1. Database
       psql "\$DATABASE_URL" < database.sql
     Into an empty database. Restoring over a populated one will conflict.

  2. Files
       copy uploads/, certificates/, course_files/, exam_data/ and the
       contents of json/ back into the project directory.

  3. Configuration
       copy config.yaml and .env back into the project directory.

     config.yaml holds the API keys and the model catalogue.
     .env holds DATABASE_URL and SESSION_SECRET. SESSION_SECRET must be the
     same value as when the backup was taken, or keys stored through
     Admin > AI Settings will not decrypt.

This backup contains live credentials. Keep it somewhere private.
TXT

echo
echo "Done: $OUT  ($(du -sh "$OUT" | cut -f1))"
echo "It contains live credentials - keep it private."
echo
