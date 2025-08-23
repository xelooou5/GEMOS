#!/usr/bin/env python3
"""
Enhanced AI Bridge - Copilot's advanced collaboration system
"""

import os
import json
from pathlib import Path
from datetime import datetime
import logging

class EnhancedAIBridge:
    def __init__(self):
        self.base_dir = Path.home() / '.gem' / 'ai_bridge'
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # Set up logging
        self.logger = self._setup_logging()
        
        # Initialize communication channels
        self.channels = {
            'gemini': self.base_dir / 'gemini.json',
            'copilot': self.base_dir / 'copilot.json',
            'amazon_q': self.base_dir / 'amazon_q.json',
            'shared': self.base_dir / 'shared.json'
        }
        
        self._initialize_channels()
        self.logger.info("Enhanced AI Bridge initialized")

    def _setup_logging(self):
        log_file = self.base_dir / 'bridge.log'
        logger = logging.getLogger('AIBridge')
        logger.setLevel(logging.INFO)
        
        # Clear existing handlers
        logger.handlers.clear()
        
        handler = logging.FileHandler(log_file)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger

    def _initialize_channels(self):
        for channel in self.channels.values():
            if not channel.exists():
                channel.write_text('[]')

    def send_message(self, sender: str, message: str, recipients: list = None):
        """Send message to specified recipients or broadcast to all"""
        timestamp = datetime.now().isoformat()
        message_data = {
            'timestamp': timestamp,
            'sender': sender,
            'content': message
        }

        # Always log to sender's channel
        self._append_to_channel(self.channels[sender], message_data)
        
        # Log to shared channel
        self._append_to_channel(self.channels['shared'], message_data)
        
        if recipients:
            for recipient in recipients:
                if recipient in self.channels:
                    self._append_to_channel(self.channels[recipient], message_data)

    def get_messages(self, ai_name: str = None, last_n: int = None) -> list:
        """Get messages for specific AI or all messages"""
        if ai_name:
            if ai_name not in self.channels:
                return []
            messages = self._read_channel(self.channels[ai_name])
        else:
            messages = self._read_channel(self.channels['shared'])
            
        if last_n:
            messages = messages[-last_n:]
        return messages

    def _append_to_channel(self, channel: Path, message: dict):
        try:
            messages = self._read_channel(channel)
            messages.append(message)
            # Keep only last 100 messages to prevent file bloat
            messages = messages[-100:]
            channel.write_text(json.dumps(messages, indent=2))
            self.logger.info(f"Message added to {channel.name}")
        except Exception as e:
            self.logger.error(f"Error writing to {channel}: {str(e)}")

    def _read_channel(self, channel: Path) -> list:
        try:
            return json.loads(channel.read_text())
        except:
            return []

# Test the bridge
if __name__ == "__main__":
    bridge = EnhancedAIBridge()
    
    # Test message from Copilot
    bridge.send_message(
        sender='copilot',
        message='Enhanced AI Bridge system implemented with logging and multi-channel support',
        recipients=['gemini', 'amazon_q']
    )
    
    # Verify messages
    print("✅ Enhanced AI Bridge initialized!")
    print(f"📁 Bridge directory: {bridge.base_dir}")
    print("📊 Shared messages:", len(bridge.get_messages()))
    print("🤖 Copilot messages:", len(bridge.get_messages('copilot')))