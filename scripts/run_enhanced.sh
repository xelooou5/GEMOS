#!/bin/bash
# 🚀 GEM OS Enhanced Runner
set -e

echo "💎 Starting GEM OS Enhanced Mode"

# Setup environment
if [ ! -f .env ]; then
    cp .env.template .env
    echo "📝 Edit .env with your API keys"
fi

# Activate venv and install
source .venv/bin/activate 2>/dev/null || python3 -m venv .venv && source .venv/bin/activate
pip install -q -r requirements.txt

# Start enhanced GEM OS
python scripts/dev_enhanced.py