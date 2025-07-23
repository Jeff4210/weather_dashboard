#!/bin/bash

SOURCE="/home/jeff/weather/output/goes19"
DEST="/mnt/ssd/goes19-archive"
AGE_DAYS=90
LOG="/home/jeff/logs/cleanup_goes19.log"

echo "[START CLEANUP] $(date)" >> "$LOG"

cd "$SOURCE" || exit 1

find . -type f -iname '*.jpg' -mtime +"$AGE_DAYS" -size +10k -print0 \
| while IFS= read -r -d '' file; do
    # Only delete if the file exists in SSD archive
    if [ -f "$DEST/$file" ]; then
        echo "[DELETING] $file" >> "$LOG"
        rm "$file"
    else
        echo "[SKIPPED] $file (not archived yet)" >> "$LOG"
    fi
done
