#!/bin/bash

# 🔥 CURSOR LINEAR INTEGRATION RUNNER
# Execute Cursor as Linear team coordinator

echo "🔥 CURSOR LINEAR INTEGRATION - GEM OS PROJECT"
echo "=============================================="
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found. Please install Python3."
    exit 1
fi

echo "🚀 Starting Cursor Linear Integration..."
echo ""

# Run the Cursor startup script
python3 cursor_startup.py

echo ""
echo "🔥 CURSOR LINEAR INTEGRATION COMPLETE!"
echo "📋 Check Linear app for all created issues"
echo "👥 AI team coordination is now active"
echo ""
echo "🎯 NEXT: AI team members start their assigned tasks"