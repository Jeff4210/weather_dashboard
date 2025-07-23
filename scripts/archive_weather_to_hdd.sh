#!/bin/bash
#
# archive_weather_to_hdd.sh
#   – Move files older than 14 days from SSD → HDD (preserving structure)
#   – Purge files older than 90 days on SSD
#   – Clean up empty directories (except lost+found)

# ─── Configuration ────────────────────────────────────────────────────────────
SSD="/home/jeff/weather/output"             # your live data root (GOES + STPI)
HDD="/home/jeff/weather/output/hdd"         # your 4 TB cold-storage mount
KEEP_DAYS=14                                # move any file older than this
DELETE_DAYS=90                              # delete SSD files older than this

LOGDIR="/home/jeff/logs"
LOGFILE="$LOGDIR/archive_to_hdd.log"
mkdir -p "$LOGDIR" "$HDD"

echo "[INFO] Starting HDD tiering at $(date)" >> "$LOGFILE"

# ─── Step 1: Copy old files to HDD ────────────────────────────────────────────
echo "[INFO] Copying files older than $KEEP_DAYS days to HDD..." >> "$LOGFILE"
find "$SSD" -type f -mtime +"$KEEP_DAYS" -print0 \
| while IFS= read -r -d '' file; do
    rel="${file#$SSD/}"
    dest="$HDD/$rel"
    mkdir -p "$(dirname "$dest")"
    if cp -u "$file" "$dest"; then
        echo "[COPIED] $file → $dest" >> "$LOGFILE"
    else
        echo "[ERROR] Failed to copy $file" >> "$LOGFILE"
    fi
done

# ─── Step 2: Delete very old files from SSD ──────────────────────────────────
echo "[INFO] Deleting files older than $DELETE_DAYS days from SSD..." >> "$LOGFILE"
find "$SSD" -type f -mtime +"$DELETE_DAYS" -print0 \
| while IFS= read -r -d '' file; do
    if rm "$file"; then
        echo "[DELETED] $file" >> "$LOGFILE"
    else
        echo "[ERROR] Failed to delete $file" >> "$LOGFILE"
    fi
done

# ─── Step 3: Clean up empty directories (skip lost+found) ────────────────────
# Prune the protected lost+found, then rmdir any other truly empty dirs
find "$SSD" -mindepth 1 -type d ! -path "$SSD/lost+found" -empty -exec rmdir {} + 2>/dev/null
find "$HDD" -mindepth 1 -type d ! -path "$HDD/lost+found" -empty -exec rmdir {} + 2>/dev/null

echo "[INFO] HDD tiering finished at $(date)" >> "$LOGFILE"
