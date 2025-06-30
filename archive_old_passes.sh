#!/bin/bash
# Archive or delete old PNGs

TARGET_DIR="static"
DAYS=2

find "$TARGET_DIR" -type f -name "*.png" -mtime +$DAYS -exec rm {} \;
