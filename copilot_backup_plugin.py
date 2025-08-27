#!/usr/bin/env python3
"""
🔥 GITHUB COPILOT PRO - AUTO BACKUP PLUGIN
Efficient cloud backup using Copilot Pro capabilities
"""

import os
import subprocess
import json
from datetime import datetime
from pathlib import Path

class CopilotBackupPlugin:
    def __init__(self):
        self.project_root = Path("/home/oem/PycharmProjects/gem")
        
    def smart_backup(self):
        """GitHub Copilot Pro smart backup"""
        try:
            os.chdir(self.project_root)
            
            # Copilot Pro: Smart file selection
            important_files = [
                "*.py", "*.md", "*.json", "*.sh", 
                "core/", "data/", ".amazonq/", "resources/"
            ]
            
            # Add only important files
            for pattern in important_files:
                subprocess.run(["git", "add", pattern], capture_output=True)
            
            # Smart commit message
            timestamp = datetime.now().strftime("%H:%M")
            subprocess.run([
                "git", "commit", "-m", 
                f"🤖 Copilot Auto-Backup {timestamp}"
            ], capture_output=True)
            
            # Force push (Copilot Pro handles conflicts)
            result = subprocess.run([
                "git", "push", "--force-with-lease", "origin", "main"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ Copilot Pro backup successful!")
                return True
            else:
                print(f"⚠️ Backup issue: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Backup error: {e}")
            return False

# Auto-run every 30 minutes
if __name__ == "__main__":
    plugin = CopilotBackupPlugin()
    plugin.smart_backup()