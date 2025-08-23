#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
💎 GEM OS - AI Agent Integrations (bridge/ai_agents.py)
Standardized classes for each AI to interact with the bridge.
"""

from .ai_bridge import EnhancedAIBridge
from typing import List, Dict, Any

class AIAgent:
    """Base class for an AI assistant interacting with the bridge."""
    def __init__(self, name: str, bridge: EnhancedAIBridge):
        self.name = name
        self.bridge = bridge
        self.log_startup()

    def log_startup(self):
        """Logs a message indicating the agent is online."""
        self.send_message(f"{self.name.replace('_', ' ').title()} connected and ready.")

    def send_message(self, content: str, recipients: List[str] = None):
        """Sends a message to the bridge."""
        # Default recipients are all other AIs
        if recipients is None:
            recipients = [ai for ai in self.bridge.channels.keys() if ai not in [self.name, 'shared']]
        self.bridge.send_message(sender=self.name, content=content, recipients=recipients)

    def review_shared_log(self, last_n: int = 20) -> List[Dict[str, Any]]:
        """Reviews the shared communication channel."""
        print(f"[{self.name}] Reviewing the last {last_n} messages from the shared log...")
        return self.bridge.get_messages(channel_name='shared', last_n=last_n)

    def acknowledge(self, message: Dict[str, Any]):
        """Acknowledges a specific message from another agent."""
        self.bridge.acknowledge_message(acknowledger=self.name, message_to_ack=message)
        print(f"[{self.name}] Acknowledged message from [{message.get('sender')}]")

class GeminiAgent(AIAgent):
    """Integration for Gemini."""
    def __init__(self, bridge: EnhancedAIBridge):
        super().__init__('gemini', bridge)

class CopilotAgent(AIAgent):
    """Integration for GitHub Copilot."""
    def __init__(self, bridge: EnhancedAIBridge):
        super().__init__('copilot', bridge)

class AmazonQAgent(AIAgent):
    """Integration for Amazon Q."""
    def __init__(self, bridge: EnhancedAIBridge):
        super().__init__('amazon_q', bridge)