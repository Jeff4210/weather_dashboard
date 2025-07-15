#!/bin/bash

SOURCE="/home/jeff/weather/output/goes19/"
DEST="/mnt/ssd/goes19-archive/"
MINUTES_OLD=3

echo "[INFO] Starting archive at $(date)"

# Find image files older than X minutes and rsync them
find "$SOURCE" -type f -mmin +$MINUTES_OLD -print0 |
  rsync -av --remove-source-files --files-from=- --from0 "$SOURCE" "$DEST"

# Remove empty directories from spacepi mount
find "$SOURCE" -type d -empty -delete

echo "[INFO] Archive complete at $(date)"
