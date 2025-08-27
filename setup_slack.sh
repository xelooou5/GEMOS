#!/bin/bash
# GEM OS - Slack Integration Setup

echo "🔥 Setting up GEM OS Slack Events..."

# Install required packages
pip install flask requests

# Start the events server
echo "Starting Slack Events server on port 3000..."
python3 slack_events.py &

echo "✅ Server running at http://localhost:3000/slack/events"
echo "Use ngrok or similar to expose this URL to Slack"
echo "Example: ngrok http 3000"