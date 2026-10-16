#!/bin/sh
# Scheduler of the backup container: runs `backup.sh run` every day at BACKUP_TIME (TZ).
set -eu

date +%s > /cache/started
while true; do
  now=$(date +%s)
  target=$(date -d "$(date +%Y-%m-%d) ${BACKUP_TIME}" +%s)
  if [ "$target" -le "$now" ]; then
    target=$((target + 86400))
  fi
  sleep $((target - now))
  # A failed run is logged (backup_failed) and alerted; the next run is tomorrow.
  /usr/local/bin/backup.sh run || true
done
