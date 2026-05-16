#!/bin/bash

# Investor Center - Streamlit Application Runner
# This script starts the Streamlit application

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Change to the script directory
cd "$SCRIPT_DIR"

# Install required dependencies
pip install -r requirements.txt

# Check if main.py exists
if [ ! -f "main.py" ]; then
    echo "Error: main.py not found in $SCRIPT_DIR"
    exit 1
fi

# Check if streamlit is installed
if ! command -v streamlit &> /dev/null; then
    echo "Error: streamlit is not installed or not in PATH"
    echo "Please install streamlit using: pip install streamlit"
    exit 1
fi

# Run the Streamlit application
echo "Starting Investor Center application..."
echo "Press Ctrl+C to stop the application"
echo ""

streamlit run main.py --server.address 0.0.0.0 --server.port "${PORT:-8501}"