#!/usr/bin/env python3
"""
Monitor Copilot background activity
"""

import time
import json
import subprocess
from datetime import datetime
from pathlib import Path

def monitor_copilot():
    """Monitor Copilot daemon activity"""
    
    log_file = Path("copilot_daemon.log")
    status_file = Path("copilot_status.json")
    
    while True:
        status = {
            "timestamp": datetime.now().isoformat(),
            "daemon_running": Path("copilot_daemon.pid").exists(),
            "files_created": len(list(Path(".").glob("gem_*.py"))),
            "last_commit": get_last_commit(),
            "copilot_active": True
        }
        
        with open(status_file, "w") as f:
            json.dump(status, f, indent=2)
        
        print(f"🤖 Copilot Status: {status}")
        time.sleep(60)

def get_last_commit():
    """Get last commit info"""
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%H %s"],
            capture_output=True, text=True
        )
        return result.stdout.strip()
    except:
        return "No commits"

if __name__ == "__main__":
    monitor_copilot()
