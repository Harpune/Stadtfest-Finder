#!/bin/sh
# Backup of PostgreSQL and the object storage with restic (ADR 0021).
#   backup.sh run      dump the database, mirror the image bucket, back up both, apply retention
#   backup.sh health   healthy if the last success is < 26 h old (or the container is new)
#   backup.sh init     create the restic repository once
# Logs are JSON lines with an `event` key like the backend logs (Grafana alerts, ADR 0020).
# Environment: PG* (pg_dump), RESTIC_REPOSITORY, RESTIC_PASSWORD, BACKUP_KEEP_WITHIN,
# S3_BUCKET and the rclone remote `objects` (RCLONE_CONFIG_OBJECTS_*, the SeaweedFS S3 API).
set -eu

LAST_SUCCESS=/cache/last-success
# Local mirror of the bucket; rclone only transfers changes. The S3 API gives a consistent
# view, unlike a copy of the live SeaweedFS files (failed the restore drill).
OBJECTS=/cache/objects
MAX_AGE_SECONDS=93600 # 26 hours

log() {
  printf '{"timestamp":"%s","level":"%s","event":"%s"%s}\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$1" "$2" "${3:-}"
}

run() {
  start=$(date +%s)
  # The dump goes straight into the encrypted repository; no plain copy on disk.
  if restic backup --quiet --host stadtfest --tag postgres \
      --stdin-from-command --stdin-filename stadtfest.dump -- \
      pg_dump --format=custom --no-owner --no-privileges \
    && rclone sync --quiet "objects:${S3_BUCKET}" "$OBJECTS" \
    && restic backup --quiet --host stadtfest --tag objects "$OBJECTS" \
    && restic forget --quiet --host stadtfest --keep-within "$BACKUP_KEEP_WITHIN" --prune; then
    date +%s > "$LAST_SUCCESS"
    log info backup_succeeded ",\"duration_s\":$(($(date +%s) - start))"
  else
    log error backup_failed ",\"duration_s\":$(($(date +%s) - start))"
    return 1
  fi
  # Weekly integrity check of the repository structure (Sunday).
  if [ "$(date +%u)" = 7 ]; then
    if restic check --quiet; then
      log info backup_check_succeeded
    else
      log error backup_check_failed
      return 1
    fi
  fi
}

health() {
  now=$(date +%s)
  if [ -f "$LAST_SUCCESS" ]; then
    [ $((now - $(cat "$LAST_SUCCESS"))) -lt "$MAX_AGE_SECONDS" ]
  else
    # No backup yet: healthy until the first scheduled run is overdue.
    [ $((now - $(cat /cache/started 2>/dev/null || echo 0))) -lt "$MAX_AGE_SECONDS" ]
  fi
}

case "${1:-}" in
  run) run ;;
  health) health ;;
  init) restic init ;;
  *)
    echo "usage: backup.sh run|health|init" >&2
    exit 2
    ;;
esac
