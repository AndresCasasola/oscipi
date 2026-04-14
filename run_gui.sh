#!/bin/bash

echo "[1/3] Checking for Python environment..."

# 1. Create a virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# 2. Activate the environment and sync dependencies
echo "[2/3] Syncing dependencies..."
source venv/bin/activate
pip install -q -r requirements.txt

# 3. Launch the application
echo "[3/3] Launching Oscilloscope..."
python3 gui/main_ui.py

# Deactivate venv after closing the app
deactivate