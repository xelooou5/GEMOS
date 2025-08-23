#!/usr/bin/env python3
"""
🔗 PyCharm AI Bridge
Monitor and share conversations between Amazon Q, Gemini, and GitHub Copilot
"""

import os
import json
import time
import subprocess
from pathlib import Path
from ai_collaboration_hub import hub, amazon_q_log

class PyCharmAIBridge:
    def __init__(self):
        self.home = Path.home()
        self.pycharm_logs = self._find_pycharm_logs()
        self.gemini_history = self._find_gemini_history()
        self.copilot_logs = self._find_copilot_logs()
        
    def _find_pycharm_logs(self) -> Path:
        """Find PyCharm log directory"""
        possible_paths = [
            self.home / ".cache/JetBrains/PyCharm*/logs",
            self.home / ".local/share/JetBrains/PyCharm*/logs",
            self.home / "Library/Logs/JetBrains/PyCharm*",  # macOS
        ]
        
        for pattern in possible_paths:
            matches = list(Path("/").glob(str(pattern)))
            if matches:
                return matches[0]
        
        return self.home / ".pycharm_logs"
    
    def _find_gemini_history(self) -> Path:
        """Find Gemini chat history (browser-based)"""
        # Chrome/Chromium history locations
        possible_paths = [
            self.home / ".config/google-chrome/Default/Local Storage",
            self.home / ".config/chromium/Default/Local Storage",
            self.home / "Library/Application Support/Google/Chrome/Default/Local Storage",  # macOS
        ]
        
        for path in possible_paths:
            if path.exists():
                return path
        
        return self.home / ".gemini_history"
    
    def _find_copilot_logs(self) -> Path:
        """Find GitHub Copilot logs"""
        possible_paths = [
            self.home / ".vscode/extensions/github.copilot*/logs",
            self.home / ".local/share/JetBrains/PyCharm*/github-copilot",
        ]
        
        for pattern in possible_paths:
            matches = list(Path("/").glob(str(pattern)))
            if matches:
                return matches[0]
        
        return self.home / ".copilot_logs"
    
    def start_monitoring(self):
        """Start monitoring all AI conversations"""
        print("🔗 Starting PyCharm AI Bridge...")
        print(f"📁 PyCharm logs: {self.pycharm_logs}")
        print(f"🤖 Gemini history: {self.gemini_history}")
        print(f"👨‍💻 Copilot logs: {self.copilot_logs}")
        
        # Create monitoring script
        self._create_monitor_script()
        
        # Start background monitoring
        self._start_background_monitor()
        
        amazon_q_log("PyCharm AI Bridge started - monitoring all AI conversations")
    
    def _create_monitor_script(self):
        """Create a script to monitor AI conversations"""
        monitor_script = """#!/bin/bash
# AI Conversation Monitor
LOG_DIR="/home/oem/.ai_collaboration"
MONITOR_LOG="$LOG_DIR/monitor.log"

echo "Starting AI conversation monitoring..." >> "$MONITOR_LOG"

# Monitor PyCharm logs
if [ -d "$HOME/.cache/JetBrains" ]; then
    find "$HOME/.cache/JetBrains" -name "*.log" -newer "$LOG_DIR/last_check" 2>/dev/null | while read logfile; do
        if grep -q "copilot\|gemini\|ai" "$logfile" 2>/dev/null; then
            echo "AI activity detected in: $logfile" >> "$MONITOR_LOG"
        fi
    done
fi

# Update timestamp
touch "$LOG_DIR/last_check"
"""
        
        script_path = "/home/oem/.ai_collaboration/monitor.sh"
        with open(script_path, 'w') as f:
            f.write(monitor_script)
        
        os.chmod(script_path, 0o755)
    
    def _start_background_monitor(self):
        """Start background monitoring process"""
        try:
            subprocess.Popen([
                "bash", "-c", 
                "while true; do /home/oem/.ai_collaboration/monitor.sh; sleep 30; done"
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print("✅ Background monitoring started")
        except Exception as e:
            print(f"⚠️ Could not start background monitoring: {e}")
    
    def share_context_with_ais(self):
        """Share recent context between all AIs"""
        context = hub.get_recent_messages(10)
        
        # Create a shared context file that all AIs can read
        context_file = "/home/oem/.ai_collaboration/shared_context.md"
        
        with open(context_file, 'w') as f:
            f.write("# Shared AI Context\n\n")
            f.write("This file contains recent conversations between all AI assistants.\n\n")
            
            for msg in context:
                f.write(f"## {msg['ai']} ({msg['timestamp']})\n")
                f.write(f"{msg['message']}\n\n")
                if msg['context']:
                    f.write(f"**Context:** {json.dumps(msg['context'], indent=2)}\n\n")
                f.write("---\n\n")
        
        print(f"📄 Shared context updated: {context_file}")
        return context_file

def setup_ai_collaboration():
    """Setup AI collaboration in PyCharm"""
    bridge = PyCharmAIBridge()
    bridge.start_monitoring()
    
    # Create instructions for other AIs
    instructions = """
# AI Collaboration Instructions

## For Gemini:
Add this to your prompts: "Check /home/oem/.ai_collaboration/shared_context.md for recent AI conversations"

## For GitHub Copilot:
Add this comment in your code: // AI Context: see /home/oem/.ai_collaboration/shared_context.md

## For Amazon Q:
This system is already integrated!

## Shared Files:
- `/home/oem/.ai_collaboration/shared_context.md` - Recent conversations
- `/home/oem/.ai_collaboration/conversation.md` - Full conversation log
- `/home/oem/.ai_collaboration/shared_conversation.json` - Machine-readable log
"""
    
    with open("/home/oem/.ai_collaboration/README.md", 'w') as f:
        f.write(instructions)
    
    return bridge

if __name__ == "__main__":
    bridge = setup_ai_collaboration()
    print("\n🤖 AI Collaboration Hub is now active!")
    print("All three AIs can now see each other's conversations!")
    print("\nNext steps:")
    print("1. Tell Gemini to check /home/oem/.ai_collaboration/shared_context.md")
    print("2. Tell Copilot to reference the shared context file")
    print("3. Start coding together!")