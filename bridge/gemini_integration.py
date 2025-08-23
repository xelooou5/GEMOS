#!/usr/bin/env python3
"""
Gemini Integration - For Gemini to collaborate with GEM OS
"""

from .enhanced_ai_bridge import EnhancedAIBridge

class GeminiIntegration:
    def __init__(self):
        self.bridge = EnhancedAIBridge()
        self.name = 'gemini'
        # Register presence
        self.bridge.send_message(
            sender=self.name,
            message="Gemini connected and ready for GEM OS collaboration",
            recipients=['copilot', 'amazon_q']
        )

    def send_message(self, message: str):
        """Send message to other AIs"""
        self.bridge.send_message(
            sender=self.name,
            message=message,
            recipients=['copilot', 'amazon_q']
        )

    def get_messages(self, last_n: int = 10):
        """Get latest messages from all AIs"""
        return self.bridge.get_messages(last_n=last_n)
    
    def get_gem_status(self):
        """Get current GEM OS status from Amazon Q"""
        messages = self.get_messages(20)
        gem_messages = [msg for msg in messages if msg['sender'] == 'amazon_q' and 'GEM' in msg['content']]
        return gem_messages[-1] if gem_messages else None

# Initialize Gemini integration
gemini = GeminiIntegration()

# Send initial message
gemini.send_message("""
Gemini ready for GEM OS collaboration!

I can help with:
- Code analysis and optimization
- Feature suggestions and improvements
- Documentation and explanations
- Problem-solving and debugging
- Creative solutions for accessibility features

What should we work on together?
""")

if __name__ == "__main__":
    print("🤖 Gemini Integration Active!")
    print("\n📨 Recent AI Messages:")
    messages = gemini.get_messages()
    for msg in messages[-3:]:
        print(f"[{msg['sender']}]: {msg['content'][:80]}...")
    
    print(f"\n📊 Total messages: {len(messages)}")
    print("✅ Ready for AI collaboration!")