#!/usr/bin/env bash
set -e

# create directories
mkdir -p uploads
mkdir -p data

# initialize JSON files if empty
if [ ! -s data/albums.json ]; then
  echo '{"albums": []}' > data/albums.json
fi

if [ ! -s data/spin_state.json ]; then
  echo '{}' > data/spin_state.json
fi

echo "Directories initialized."
