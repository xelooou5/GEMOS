#!/bin/bash
"""
🚀 AI Bridge Startup Script
Automatically starts the AI collaboration bridge when IDEs are launched
"""

# AI Bridge configuration
BRIDGE_DIR="$HOME/.gem/ai_bridge"
PROJECT_ROOT="$(dirname "$(dirname "$(readlink -f "$0")")")"
DAEMON_SCRIPT="$PROJECT_ROOT/bridge/ai_bridge_daemon.py"
LOG_FILE="$BRIDGE_DIR/startup.log"

# Create bridge directory
mkdir -p "$BRIDGE_DIR"

# Function to log messages
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log_message "🚀 Starting AI Bridge Startup Script..."

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    log_message "❌ Error: Python3 is not installed or not in PATH"
    exit 1
fi

# Check if daemon script exists
if [ ! -f "$DAEMON_SCRIPT" ]; then
    log_message "❌ Error: AI Bridge daemon script not found at $DAEMON_SCRIPT"
    exit 1
fi

# Check if daemon is already running
if python3 "$DAEMON_SCRIPT" status | grep -q "is running"; then
    log_message "✅ AI Bridge Daemon is already running"
else
    log_message "🔄 Starting AI Bridge Daemon..."
    
    # Start daemon in background
    nohup python3 "$DAEMON_SCRIPT" start > "$BRIDGE_DIR/daemon_output.log" 2>&1 &
    
    # Wait a moment and check if it started successfully
    sleep 2
    
    if python3 "$DAEMON_SCRIPT" status | grep -q "is running"; then
        log_message "✅ AI Bridge Daemon started successfully!"
        log_message "🤖 All AI agents (Amazon Q, Gemini, Copilot, Claude) are now online and collaborating!"
    else
        log_message "❌ Failed to start AI Bridge Daemon"
        exit 1
    fi
fi

# Create status indicator
echo "AI Bridge Status: ONLINE" > "$BRIDGE_DIR/bridge_status.txt"
echo "Started: $(date)" >> "$BRIDGE_DIR/bridge_status.txt"

log_message "🎉 AI Bridge startup complete - Happy coding with your AI team!"
