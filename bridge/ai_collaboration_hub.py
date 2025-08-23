#!/usr/bin/env python3
"""
🤖 AI Collaboration Hub
Shared logging system for Amazon Q, Gemini, and GitHub Copilot to collaborate in PyCharm
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, List
import threading
import time

class AICollaborationHub:
    def __init__(self, log_dir: str = "/home/oem/.ai_collaboration"):
        self.log_dir = log_dir
        self.conversation_file = os.path.join(log_dir, "shared_conversation.json")
        self.lock = threading.Lock()
        
        # Create directory if it doesn't exist
        os.makedirs(log_dir, exist_ok=True)
        
        # Initialize conversation file
        if not os.path.exists(self.conversation_file):
            self._save_conversation([])
    
    def log_message(self, ai_name: str, message: str, context: Dict[str, Any] = None):
        """Log a message from any AI assistant"""
        with self.lock:
            conversation = self._load_conversation()
            
            entry = {
                "timestamp": datetime.now().isoformat(),
                "ai": ai_name,
                "message": message,
                "context": context or {},
                "id": len(conversation) + 1
            }
            
            conversation.append(entry)
            self._save_conversation(conversation)
            
            # Also write to a simple text file for easy reading
            self._update_readable_log(entry)
    
    def get_recent_messages(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent messages from all AIs"""
        conversation = self._load_conversation()
        return conversation[-limit:] if conversation else []
    
    def get_messages_by_ai(self, ai_name: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent messages from specific AI"""
        conversation = self._load_conversation()
        ai_messages = [msg for msg in conversation if msg["ai"] == ai_name]
        return ai_messages[-limit:] if ai_messages else []
    
    def _load_conversation(self) -> List[Dict[str, Any]]:
        """Load conversation from file"""
        try:
            with open(self.conversation_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []
    
    def _save_conversation(self, conversation: List[Dict[str, Any]]):
        """Save conversation to file"""
        with open(self.conversation_file, 'w') as f:
            json.dump(conversation, f, indent=2)
    
    def _update_readable_log(self, entry: Dict[str, Any]):
        """Update human-readable log file"""
        readable_file = os.path.join(self.log_dir, "conversation.md")
        
        with open(readable_file, 'a') as f:
            f.write(f"\n## {entry['ai']} - {entry['timestamp']}\n")
            f.write(f"{entry['message']}\n")
            if entry['context']:
                f.write(f"**Context:** {json.dumps(entry['context'], indent=2)}\n")
            f.write("---\n")

# Global instance
hub = AICollaborationHub()

# Convenience functions for each AI
def amazon_q_log(message: str, context: Dict[str, Any] = None):
    """Log message from Amazon Q"""
    hub.log_message("Amazon Q", message, context)

def gemini_log(message: str, context: Dict[str, Any] = None):
    """Log message from Gemini"""
    hub.log_message("Gemini", message, context)

def copilot_log(message: str, context: Dict[str, Any] = None):
    """Log message from GitHub Copilot"""
    hub.log_message("GitHub Copilot", message, context)

def get_ai_context() -> str:
    """Get recent context from all AIs for sharing"""
    recent = hub.get_recent_messages(5)
    context = "Recent AI Collaboration:\n"
    for msg in recent:
        context += f"[{msg['ai']}]: {msg['message'][:100]}...\n"
    return context

if __name__ == "__main__":
    # Test the system
    amazon_q_log("Starting AI collaboration hub", {"project": "GEM OS"})
    print("AI Collaboration Hub initialized!")
    print(f"Logs stored in: {hub.log_dir}")
    print("All AIs can now see each other's conversations!")