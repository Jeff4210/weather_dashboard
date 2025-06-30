#!/bin/bash

NOAA_SRC_DIR="$HOME/weather/output"
DST_15="$HOME/weather_dashboard/static/NOAA/15"
DST_19="$HOME/weather_dashboard/static/NOAA/19"

mkdir -p "$DST_15" "$DST_19"

# Copy latest 10 images for each satellite
find "$NOAA_SRC_DIR" -type f -iname "*137.1 MHz*.png" | sort | tail -n 10 | while read -r f; do
    cp -u "$f" "$DST_15"
done

find "$NOAA_SRC_DIR" -type f -iname "*137.62 MHz*.png" | sort | tail -n 10 | while read -r f; do
    cp -u "$f" "$DST_19"
done
