#!/bin/bash

echo "🛰️ Syncing and generating animations..."

# Source: your decoder output directory
SOURCE_DIR="/home/jeff/SatDump/output"  # <-- Update if your actual output path is different

# Target: Flask static directory
TARGET_DIR="/home/jeff/weather_dashboard/static"

# Sync GOES-19 FD + MESO CH01–CH16
for region in FD MESO; do
  for i in $(seq -w 1 16); do
    SRC_PATH="$SOURCE_DIR/GOES-19/$region/CH$i"
    DEST_PATH="$TARGET_DIR/GOES-19/$region/CH$i"
    mkdir -p "$DEST_PATH"
    if compgen -G "$SRC_PATH/*.png" > /dev/null; then
      cp "$SRC_PATH"/*.png "$DEST_PATH/"
    fi
  done
done

# Sync NOAA-15 & NOAA-19 APT
for sat in NOAA-15 NOAA-19; do
  SRC_PATH="$SOURCE_DIR/$sat/APT"
  DEST_PATH="$TARGET_DIR/$sat/APT"
  mkdir -p "$DEST_PATH"
  if compgen -G "$SRC_PATH/*.png" > /dev/null; then
    cp "$SRC_PATH"/*.png "$DEST_PATH/"
  fi
done

# Now run the animation builder
/home/jeff/weather_dashboard/make_animations.sh

echo "✅ Done."
