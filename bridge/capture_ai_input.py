#!/usr/bin/env python3
"""
Capture AI Input - Manual input system for AI collaboration
"""

import sys
import json
from datetime import datetime
from pathlib import Path

def capture_ai_input():
    """Capture input from any AI assistant"""
    print("🤖 AI Collaboration Input Capture")
    print("=" * 50)
    
    ai_name = input("Which AI? (Gemini/Copilot/Other): ").strip()
    if not ai_name:
        ai_name = "Unknown AI"
    
    print(f"\nEnter {ai_name}'s suggestions (press Ctrl+D when done):")
    print("-" * 30)
    
    try:
        content = sys.stdin.read().strip()
    except KeyboardInterrupt:
        print("\nCancelled.")
        return
    
    if not content:
        print("No content provided.")
        return
    
    # Save to shared system
    timestamp = datetime.now().isoformat()
    
    # Update shared files
    shared_dir = Path("/home/oem/.ai_shared")
    
    # Add to markdown log
    with open(shared_dir / "all_conversations.md", "a") as f:
        f.write(f"\n## {ai_name} - {timestamp}\n{content}\n---\n")
    
    # Update JSON log
    json_file = shared_dir / "conversations.json"
    try:
        with open(json_file, "r") as f:
            data = json.load(f)
    except:
        data = []
    
    data.append({
        "ai": ai_name,
        "message": content,
        "timestamp": timestamp
    })
    
    with open(json_file, "w") as f:
        json.dump(data[-50:], f, indent=2)
    
    print(f"\n✅ Captured {ai_name}'s input successfully!")
    print(f"📁 Saved to: {shared_dir}")
    
    return content

if __name__ == "__main__":
    capture_ai_input()