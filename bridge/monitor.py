#!/usr/bin/env python3
"""
AI Monitor - File system monitoring for AI collaboration
"""

import time
from pathlib import Path

class AIMonitor:
    def __init__(self):
        self.shared_dir = Path.home() / '.ai_shared'
        
    def on_modified(self, file_path):
        if file_path.endswith('.json'):
            print(f"🤖 AI Update detected in: {Path(file_path).name}")
            # Trigger sync between AIs

def start_monitoring():
    """Start monitoring without external dependencies"""
    shared_dir = Path.home() / '.ai_shared'
    monitor = AIMonitor()
    
    print(f"📁 Monitoring AI collaboration in: {shared_dir}")
    
    # Simple file monitoring without watchdog dependency
    file_times = {}
    
    def check_files():
        for file in shared_dir.glob('*.json'):
            current_time = file.stat().st_mtime
            if str(file) not in file_times:
                file_times[str(file)] = current_time
            elif file_times[str(file)] != current_time:
                monitor.on_modified(str(file))
                file_times[str(file)] = current_time
    
    return check_files