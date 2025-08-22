#!/bin/bash

echo "Starting Nostr Home Hub..."
echo ""

# Check if config has been updated
if grep -q "npub13hyx3qsqk3r7ctjqrr49uskut4yqjsxt8uvu4rekr55p08wyhf0qq90nt7" config.py; then
    echo "WARNING: Please update your npub in config.py before starting!"
    echo "   Edit config.py and replace the placeholder with your actual npub"
    echo ""
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Exiting..."
        exit 1
    fi
fi

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Check if requirements are installed
echo "Installing Python dependencies..."
pip install -r requirements.txt

echo "Starting server on http://localhost:3000"
echo "Nostr Relay: ws://localhost:3000/socket.io/"
echo "Press Ctrl+C to stop"
echo ""

# Start the Python server
python3 app.py
