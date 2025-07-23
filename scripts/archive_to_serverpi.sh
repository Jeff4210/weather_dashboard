#!/bin/bash

# Define paths
SOURCE="/home/jeff/weather/output"
DEST="/home/jeff/weather/output/archives/stpi"

# Start log
echo "[INFO] Archiving from $SOURCE to $DEST"

# Find all files (excluding output/archives and output/goes*)
find "$SOURCE" -type f \
  -not -path "$SOURCE/archives/*" \
  -not -path "$SOURCE/goes19/*" \
  -not -path "$SOURCE/goes16/*" \
  -not -path "$SOURCE/goes18/*" \
  -print0 | while IFS= read -r -d '' file; do

    rel_path="${file#$SOURCE/}"                      # Trim leading path
    dest_path="$DEST/$rel_path"                      # Build target path
    mkdir -p "$(dirname "$dest_path")"               # Ensure directory exists

    if cp -u "$file" "$dest_path"; then
        echo "[COPIED] $file → $dest_path"
        rm "$file" && echo "[DELETED] $file"
    else
        echo "[ERROR] Failed to copy $file"
    fi
done

# Clean up empty directories from SOURCE
find "$SOURCE" -depth -type d -empty \
  -not -path "$SOURCE" \
  -not -path "$SOURCE/archives*" \
  -not -path "$SOURCE/goes*" \
  -exec rmdir {} \;
