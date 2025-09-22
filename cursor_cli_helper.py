#!/usr/bin/env python3
"""
🔥 CURSOR CLI HELPER - GEM OS PROJECT
Use Cursor CLI to automate Linear integration
"""

import subprocess
import os

def check_cursor_cli():
    """Check Cursor CLI availability"""
    try:
        result = subprocess.run(["cursor", "--version"], capture_output=True, text=True)
        print(f"✅ Cursor CLI: {result.stdout.strip()}")
        return True
    except:
        print("❌ Cursor CLI not found")
        return False

def run_cursor_commands():
    """Run Cursor CLI commands for Linear integration"""
    commands = [
        "cursor --help",
        f"cursor /home/runner/work/GEMOS/GEMOS"
    ]
    
    for cmd in commands:
        print(f"💻 {cmd}")
        subprocess.run(cmd.split())

if __name__ == "__main__":
    print("🔥 CURSOR CLI HELPER")
    if check_cursor_cli():
        run_cursor_commands()
    else:
        print("Install: npm install -g @cursor/cli")