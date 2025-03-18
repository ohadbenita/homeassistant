#!/usr/bin/env bash

# Purpose:
#   1. Retrieve JSON listing of timelapse files from Moonraker
#   2. Filter to only .mp4 files (ignore .zip, .jpg, etc.)
#   3. Select the most recently modified .mp4
#   4. Trim leading/trailing spaces and newlines from the filename
#   5. URL-encode the filename
#   6. Download it via "/server/files/timelapse/<filename>"
#
# Usage:
#   ./send_latest_timelapse.sh

# Moonraker host & port
MOONRAKER_HOST="172.16.1.129"
MOONRAKER_PORT="4409"

# Where to save the file in Home Assistant
HA_WWW_PATH="/config/www"

# 1) Get the JSON listing from the timelapse root
JSON=$(curl -s "http://${MOONRAKER_HOST}:${MOONRAKER_PORT}/server/files/list?root=timelapse")
if [ -z "$JSON" ]; then
  echo "Error: Could not retrieve timelapse list from Moonraker."
  exit 1
fi

# 2) Filter out non-mp4 files, then select the file with the highest 'modified'
LATEST_MP4=$(echo "$JSON" | jq -r '
  .result
  | map(select(.path | endswith(".mp4")))
  | sort_by(.modified)
  | last
  | .path
')

if [ -z "$LATEST_MP4" ] || [ "$LATEST_MP4" = "null" ]; then
  echo "No .mp4 timelapse files found."
  exit 0
fi

# 3) Trim any leading or trailing whitespace and remove newlines
LATEST_MP4=$(echo "$LATEST_MP4" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' | tr -d '\n\r')

echo "Newest timelapse MP4 (trimmed): '$LATEST_MP4'"

# 4) URL-encode the filename in case it contains spaces or special chars
ENCODED_MP4=$(printf '%s' "$LATEST_MP4" | jq -sRr @uri)

# 5) Download using the direct "/server/files/timelapse/<ENCODED_MP4>" path
#    Save it locally with the original (trimmed) filename
curl -v -o "${HA_WWW_PATH}/3d_print_latest_timelapse.mp4" \
  "http://${MOONRAKER_HOST}:${MOONRAKER_PORT}/server/files/timelapse/${ENCODED_MP4}" 2>&1 &

if [ $? -eq 0 ]; then
  echo "Downloaded to: ${HA_WWW_PATH}/${LATEST_MP4}"
else
  echo "Failed to download the timelapse file."
  exit 1
fi

exit 0
