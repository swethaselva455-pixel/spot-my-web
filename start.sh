#!/usr/bin/env bash
set -e

echo "================================================================="
echo "      Starting SpotMyShoot Booking Server (Local Mode)"
echo "================================================================="
echo ""

if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 is not installed or not in PATH."
    exit 1
fi

echo "Checking Python dependencies..."
python3 -m pip install -q -r requirements.txt

echo "Launching application server on http://127.0.0.1:5000..."
python3 run.py
