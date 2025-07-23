#!/bin/bash

SOURCE="/home/jeff/weather/output/goes19"
DEST="/mnt/ssd/goes19-archive"
ARCHIVE_WINDOW_MINUTES=70
LOG="/home/jeff/logs/archive_goes19.log"

mkdir -p "$DEST"
echo "[START] $(date)" >> "$LOG"

cd "$SOURCE" || exit 1

find . -type f \( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' \) \
    -mmin -"$ARCHIVE_WINDOW_MINUTES" -size +10k -print0 \
| while IFS= read -r -d '' file; do
    src="$file"
    dest="$DEST/$file"
    mkdir -p "$(dirname "$dest")"
    rsync -a --remove-source-files --ignore-missing-args "$src" "$dest" \
      && echo "[MOVED] $src → $dest" >> "$LOG"
done
