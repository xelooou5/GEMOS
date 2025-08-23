#!/usr/bin/env python3
"""
🤖 Simple AI Collaboration Bridge
Share conversations between Amazon Q, Gemini, and GitHub Copilot
"""

import os
import json
from datetime import datetime
from pathlib import Path

# Create shared directory
SHARED_DIR = Path("/home/oem/.ai_shared")
SHARED_DIR.mkdir(exist_ok=True)

def log_conversation(ai_name: str, message: str):
    """Log conversation from any AI"""
    timestamp = datetime.now().isoformat()
    
    # Append to shared log
    with open(SHARED_DIR / "all_conversations.md", "a") as f:
        f.write(f"\n## {ai_name} - {timestamp}\n{message}\n---\n")
    
    # Update JSON log
    json_file = SHARED_DIR / "conversations.json"
    try:
        with open(json_file, "r") as f:
            data = json.load(f)
    except:
        data = []
    
    data.append({
        "ai": ai_name,
        "message": message,
        "timestamp": timestamp
    })
    
    with open(json_file, "w") as f:
        json.dump(data[-50:], f, indent=2)  # Keep last 50 messages

def get_recent_context():
    """Get recent context for sharing"""
    try:
        with open(SHARED_DIR / "conversations.json", "r") as f:
            data = json.load(f)
        return data[-10:]  # Last 10 messages
    except:
        return []

# Initialize
log_conversation("Amazon Q", "AI Collaboration Bridge initialized")

print(f"🤖 AI Bridge ready! Shared files in: {SHARED_DIR}")
print("\nTo share with other AIs:")
print(f"1. Gemini: Read {SHARED_DIR}/all_conversations.md")
print(f"2. Copilot: Check {SHARED_DIR}/conversations.json")
print("3. All AIs can now see each other's work!")

# Create instructions file
with open(SHARED_DIR / "instructions.md", "w") as f:
    f.write("""# AI Collaboration Instructions

## For Gemini:
Before responding, check: /home/oem/.ai_shared/all_conversations.md

## For GitHub Copilot:
Add this comment: // Context: /home/oem/.ai_shared/conversations.json

## For Amazon Q:
Already integrated! Use log_conversation() to share.

## Files:
- all_conversations.md: Human-readable log
- conversations.json: Machine-readable log
- instructions.md: This file
""")