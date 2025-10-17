#!/bin/bash
# IWM 0DTE System - Deployment Script
# This script prepares and deploys the system to Render

set -e

echo "🚀 IWM 0DTE System - Deployment Preparation"
echo "============================================="

# Check if we're in the right directory
if [ ! -f "main.py" ] || [ ! -f "render.yaml" ]; then
    echo "❌ Error: Not in the correct directory"
    echo "Please run this script from the project root directory"
    exit 1
fi

# Check Python version
echo "🐍 Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python version: $python_version"

# Install dependencies
echo "📦 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Verify dependencies
echo "🔍 Verifying dependencies..."
python3 -c "import websocket, requests, numpy, pytz, cryptography; print('✅ All dependencies verified')"

# Check render.yaml configuration
echo "⚙️ Checking Render configuration..."
if grep -q "healthCheckPath" render.yaml; then
    echo "✅ Health check endpoint configured"
else
    echo "❌ Health check endpoint not configured"
    exit 1
fi

if grep -q "pytz" requirements.txt; then
    echo "✅ pytz dependency included"
else
    echo "❌ pytz dependency missing"
    exit 1
fi

echo "✅ Deployment preparation complete!"
echo ""
echo "📋 Next steps:"
echo "1. Commit and push your changes to GitHub"
echo "2. Render will automatically deploy using render.yaml"
echo "3. Monitor the deployment logs in Render dashboard"
echo "4. Test the health endpoint after deployment"