#!/bin/bash
# Delete GOES .jpgs older than 1 day

TARGET="/home/jeff/weather/output/goes19"

find "$TARGET" -type f -name "*.jpg" -mtime +1 -delete
