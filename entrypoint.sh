#!/bin/bash

# Run the script once at startup to generate the first index.html
python3 /app/version_check.py

# Start Nginx in the background
nginx

# Infinite loop to update every 6 hours (21600 seconds)
while true; do
  sleep 21600
  python3 /app/version_check.py
  echo "Dashboard updated at $(date)"
done