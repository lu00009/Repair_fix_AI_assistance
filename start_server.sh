#!/bin/bash
# Startup script for the Repair Assistant API

# Navigate to project root
cd "$(dirname "$0")"

# Activate virtual environment
source venv/bin/activate

# Run the server
echo "Starting Repair Assistant API..."
echo "Server will be available at http://localhost:8000"
echo "API docs at http://localhost:8000/docs"
echo ""

uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
