#!/usr/bin/env python3
"""
Copilot Integration - GitHub Copilot's integration module
"""

from .enhanced_ai_bridge import EnhancedAIBridge

class CopilotIntegration:
    def __init__(self):
        self.bridge = EnhancedAIBridge()
        self.name = 'copilot'
        # Register presence
        self.bridge.send_message(
            sender=self.name,
            message="GitHub Copilot connected and ready for GEM OS collaboration",
            recipients=['gemini', 'amazon_q']
        )

    def send_message(self, message: str):
        """Send message to other AIs"""
        self.bridge.send_message(
            sender=self.name,
            message=message,
            recipients=['gemini', 'amazon_q']
        )

    def get_messages(self, last_n: int = 10):
        """Get latest messages from all AIs"""
        return self.bridge.get_messages(last_n=last_n)
    
    def get_context(self):
        """Get conversation context for better collaboration"""
        messages = self.get_messages(20)
        context = "Recent AI Collaboration Context:\n"
        for msg in messages[-5:]:  # Last 5 messages
            context += f"[{msg['sender']}]: {msg['content'][:100]}...\n"
        return context

# Initialize Copilot integration
copilot = CopilotIntegration()

# Log Copilot's suggestions for GEM OS
copilot.send_message("""
Copilot Suggestions for GEM OS Enhancement:

1. Enhanced AI Bridge System ✅ - Implemented with logging and multi-channel support
2. Real-time collaboration between all 3 AIs
3. Structured message passing with timestamps
4. Persistent conversation history
5. Context sharing for better collaboration

Ready to collaborate on GEM OS improvements!
""")

if __name__ == "__main__":
    # Display recent messages
    print("🤖 GitHub Copilot Integration Active!")
    print("\n📨 Recent AI Messages:")
    messages = copilot.get_messages()
    for msg in messages:
        print(f"[{msg['timestamp'][:19]}] {msg['sender']}: {msg['content'][:80]}...")
    
    print(f"\n📊 Total messages: {len(messages)}")
    print("✅ Ready for AI collaboration!")