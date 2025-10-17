#!/bin/bash
# Quick start script for IWM Momentum System

set -e

echo "🚀 IWM 0DTE Momentum System - Startup"
echo "======================================"

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    echo "📝 Copy .env.example to .env and fill in your credentials:"
    echo "   cp .env.example .env"
    exit 1
fi

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python version: $python_version"

# Check if requirements are installed
if ! python3 -c "import websocket, requests, numpy, pytz" 2>/dev/null; then
    echo "⚠️  Missing dependencies. Installing..."
    pip install -r requirements.txt
fi

# Create logs directory
mkdir -p logs

# Validate configuration
echo ""
echo "🔍 Validating configuration..."
python3 config.py

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Configuration validation failed!"
    echo "   Check your .env file and ensure all required keys are set:"
    echo "   - POLYGON_API_KEY"
    echo "   - PUSHOVER_TOKEN"
    echo "   - PUSHOVER_USER_KEY"
    exit 1
fi

echo ""
echo "✓ Configuration valid"
echo ""
echo "======================================"
echo "🟢 Starting IWM Momentum System..."
echo "   Press Ctrl+C to stop"
echo "======================================"
echo ""

# Start the system
python3 main.py


