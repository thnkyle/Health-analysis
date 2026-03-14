#!/bin/bash
# Quick start - run after initial setup
cd "$(dirname "$0")/backend"
echo "Server starting at http://localhost:8000"
uvicorn main:app --host 127.0.0.1 --port 8000
