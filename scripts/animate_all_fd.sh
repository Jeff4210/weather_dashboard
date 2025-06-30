#!/bin/bash

INPUT_BASE="/home/jeff/weather/output/goes19/fd"
OUTPUT_BASE="/home/jeff/weather_dashboard/static/GOES19/fd"

# Find only real channel folders (ch02, ch03, ..., ch16)
for ch_dir in "$INPUT_BASE"/ch*; do
    [ -d "$ch_dir" ] || continue
    ch=$(basename "$ch_dir")

    IN_DIR="$INPUT_BASE/$ch"
    OUT_DIR="$OUTPUT_BASE/$ch"
    mkdir -p "$OUT_DIR"

    CLEAN_IMAGES=$(find "$IN_DIR" -type f -name '*_clean.jpg' | sort | tail -n 10)
    MAP_IMAGES=$(find "$IN_DIR" -type f -name '*_map.jpg' | sort | tail -n 10)

    if [ -n "$CLEAN_IMAGES" ]; then
        convert -delay 20 -loop 0 $CLEAN_IMAGES "$OUT_DIR/animation_clean.gif"
    fi

    if [ -n "$MAP_IMAGES" ]; then
        convert -delay 20 -loop 0 $MAP_IMAGES "$OUT_DIR/animation_map.gif"
    fi
done
