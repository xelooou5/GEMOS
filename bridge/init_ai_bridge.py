#!/usr/bin/env python3
"""
Initialize AI Bridge - Setup enhanced AI collaboration
"""

import time
from ai_bridge import AIBridge
from monitor import start_monitoring

def initialize_ai_collaboration():
    bridge = AIBridge()
    monitor_func = start_monitoring()
    
    print("🤖 Enhanced AI Bridge initialized!")
    print(f"\nShared Directory: {bridge.shared_dir}")
    print("\nActive Files:")
    for name, file in bridge.files.items():
        print(f"- {name}: {file}")
    
    # Update context with current GEM OS status
    bridge.update_context({
        "project": "GEM OS Enhancement",
        "status": "Running with revolutionary features",
        "current_focus": "AI collaboration and feature integration",
        "last_update": time.time()
    })
    
    return bridge, monitor_func

if __name__ == "__main__":
    bridge, monitor = initialize_ai_collaboration()
    
    print("\n✅ AI Bridge ready for collaboration!")
    print("\nPress Ctrl+C to stop monitoring...")
    
    try:
        while True:
            monitor()  # Check for file changes
            time.sleep(2)
    except KeyboardInterrupt:
        print("\n👋 AI Bridge stopped.")