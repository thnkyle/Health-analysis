#!/bin/bash
# Health Analysis - Termux Setup Script
# Run this in Termux on your Android phone

set -e

echo "=== Health Analysis - Termux Setup ==="
echo ""

# Update packages
echo "[1/5] Updating Termux packages..."
pkg update -y && pkg upgrade -y

# Install Python + scientific packages via pkg (NOT pip — pip builds from source and hangs)
echo "[2/5] Installing Python and dependencies..."
pkg install -y python git python-numpy python-pandas

# Clone the repo (skip if already cloned)
echo "[3/5] Getting the project..."
if [ ! -d "$HOME/Health-analysis" ]; then
    git clone https://github.com/thnkyle/Health-analysis.git "$HOME/Health-analysis"
else
    echo "  Project already exists, pulling latest..."
    cd "$HOME/Health-analysis" && git pull origin claude/health-connect-api-1xxgb || true
fi

cd "$HOME/Health-analysis/backend"

# Install remaining Python dependencies via pip (these are pure Python, install fast)
echo "[4/5] Installing Python dependencies..."
pip install --upgrade pip
pip install fastapi uvicorn sqlalchemy pydantic

# Start the server
echo ""
echo "[5/5] Starting server..."
echo "=================================="
echo "  Open in your browser:"
echo "  http://localhost:8000"
echo "=================================="
echo ""
uvicorn main:app --host 127.0.0.1 --port 8000
