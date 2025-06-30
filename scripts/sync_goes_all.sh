#!/bin/bash

SRC_USER="jeff"
SRC_HOST="100.124.246.6"
SRC_BASE="/home/jeff/goes19"
DEST_BASE="/home/jeff/weather/output/goes19"
TODAY=$(date -u +%Y%m%d)

echo "🔍 Discovering available channels..."

CHANNELS=$(ssh ${SRC_USER}@${SRC_HOST} "find ${SRC_BASE} -type f -name '*${TODAY}*.jpg' | sed 's|.*/goes19/||' | sed 's|/[^/]*$||' | sort -u")

for CHANNEL in $CHANNELS; do
    SRC_PATH="${SRC_BASE}/${CHANNEL}"
    DEST_PATH="${DEST_BASE}/${CHANNEL}"

    echo "🔄 Syncing ${CHANNEL}..."
    mkdir -p "$DEST_PATH"

    rsync -az --include="*${TODAY}*.jpg" --exclude="*" \
        ${SRC_USER}@${SRC_HOST}:"${SRC_PATH}/" "${DEST_PATH}/"
done

echo "✅ Sync complete."
