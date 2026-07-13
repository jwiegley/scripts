#!/usr/bin/env bash
# purge-stale-files.sh — remove DB entries for files no longer on disk
# Usage:
#   ./purge-stale-files.sh --dry-run   # show what would be deleted (default)
#   ./purge-stale-files.sh --execute   # actually delete
#
# Connects to the org database on postgres.vulcan.lan using Keychain password.

set -euo pipefail

MODE="${1:---dry-run}"
if [[ "$MODE" != "--dry-run" && "$MODE" != "--execute" ]]; then
  echo "Usage: $0 [--dry-run | --execute]" >&2
  exit 1
fi

PW=$(security find-generic-password -a org -w)
export PGPASSWORD="$PW"
PSQL="psql -h postgres.vulcan.lan -p 5432 -U johnw -d org -X"

echo "=== Purge stale files from org database ==="
echo "Mode: $MODE"
echo ""

# Step 1: Collect all file paths from the DB into a temp file
TMPFILES=$(mktemp)
trap 'rm -f "$TMPFILES"' EXIT

$PSQL -t -A -c "SELECT path FROM files;" > "$TMPFILES"

TOTAL_DB=$(wc -l < "$TMPFILES" | tr -d ' ')
echo "Total files in DB: $TOTAL_DB"

# Step 2: Find which ones don't exist on disk
TMPSTALE=$(mktemp)
trap 'rm -f "$TMPFILES" "$TMPSTALE"' EXIT

while IFS= read -r fpath; do
  [[ -n "$fpath" ]] || continue
  if [[ ! -e "$fpath" ]]; then
    echo "$fpath"
  fi
done < "$TMPFILES" > "$TMPSTALE"

STALE_COUNT=$(wc -l < "$TMPSTALE" | tr -d ' ')
echo "Stale files (not on disk): $STALE_COUNT"
echo ""

if [[ "$STALE_COUNT" -eq 0 ]]; then
  echo "Nothing to do. All DB files exist on disk."
  exit 0
fi

echo "Stale file paths:"
while IFS= read -r fpath; do
  echo "  $fpath"
done < "$TMPSTALE"
echo ""

# Build SQL-safe comma-separated list of paths
STALE_ESQ_LIST=$(while IFS= read -r fpath; do
  escaped="${fpath//\'/\'\'}"
  echo "'$escaped'"
done < "$TMPSTALE" | paste -sd, -)

if [[ "$MODE" == "--dry-run" ]]; then
  echo "--- DRY RUN ---"
  echo ""

  # Count everything that would be deleted
  $PSQL -F' | ' -H -c "
WITH stale_files AS (
  SELECT id, path FROM files WHERE path IN ($STALE_ESQ_LIST)
)
SELECT
  (SELECT COUNT(*) FROM stale_files) AS stale_files,
  (SELECT COUNT(*) FROM entries e JOIN stale_files sf ON sf.id = e.file_id) AS orphan_entries,
  (SELECT COUNT(*) FROM entry_tags et
   JOIN entries e ON e.id = et.entry_id
   JOIN stale_files sf ON sf.id = e.file_id) AS orphan_tags,
  (SELECT COUNT(*) FROM entry_stamps es
   JOIN entries e ON e.id = es.entry_id
   JOIN stale_files sf ON sf.id = e.file_id) AS orphan_stamps,
  (SELECT COUNT(*) FROM entry_log_entries el
   JOIN entries e ON e.id = el.entry_id
   JOIN stale_files sf ON sf.id = e.file_id) AS orphan_log_entries,
  (SELECT COUNT(*) FROM entry_embeddings ee
   JOIN entries e ON e.id = ee.entry_id
   JOIN stale_files sf ON sf.id = e.file_id) AS orphan_embeddings;
"

  echo ""
  echo "NO ACTION constraint violations that would be resolved:"
  echo ""
  echo "  entry_tags.source_id pointing to entries in stale files:"
  $PSQL -F' | ' -H -c "
  SELECT COUNT(*) AS violating_tags
  FROM entry_tags et
  JOIN entries e ON e.id = et.source_id
  JOIN files f ON f.id = e.file_id
  WHERE f.path IN ($STALE_ESQ_LIST)
    AND et.source_id IS NOT NULL;
"

  echo ""
  echo "  entry_log_entries.logbook_id pointing to logs in stale files:"
  $PSQL -F' | ' -H -c "
  SELECT COUNT(*) AS violating_logs
  FROM entry_log_entries el
  JOIN entry_log_entries parent ON parent.id = el.logbook_id
  JOIN entries e ON e.id = parent.entry_id
  JOIN files f ON f.id = e.file_id
  WHERE f.path IN ($STALE_ESQ_LIST)
    AND el.logbook_id IS NOT NULL;
"

  echo ""
  echo "Run with --execute to actually delete."
else
  echo "--- EXECUTING ---"
  echo ""

  $PSQL <<SQL
BEGIN;

-- Phase 1: Fix NO ACTION constraints
-- Null out entry_tags.source_id where the source entry is in a stale file
UPDATE entry_tags
SET source_id = NULL, is_inherited = false
WHERE source_id IN (
  SELECT e.id FROM entries e
  JOIN files f ON f.id = e.file_id
  WHERE f.path IN ($STALE_ESQ_LIST)
)
AND source_id IS NOT NULL;

-- Null out entry_log_entries.logbook_id where the parent log is in a stale file
UPDATE entry_log_entries
SET logbook_id = NULL
WHERE logbook_id IN (
  SELECT el.id FROM entry_log_entries el
  JOIN entries e ON e.id = el.entry_id
  JOIN files f ON f.id = e.file_id
  WHERE f.path IN ($STALE_ESQ_LIST)
);

-- Phase 2: Delete stale files (CASCADE removes entries + all children)
DELETE FROM files WHERE path IN ($STALE_ESQ_LIST);

COMMIT;

-- Report
SELECT
  'Files remaining in DB: ' || COUNT(*) AS status
FROM files;
SQL

  echo ""
  echo "Done. Re-run with --dry-run to verify."
fi
