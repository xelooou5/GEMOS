#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
💎 GEM OS - AI Collaboration Bridge (bridge/ai_bridge.py)
The central nervous system for AI team collaboration.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

class GEMRules:
    """Codifies the guiding principles for AI collaboration on GEM OS."""
    def __init__(self):
        self.rules = {
            1: "Mission First: All changes must align with making GEM OS a world-class, accessible tool for people in need.",
            2: "Build, Don't Break: Never remove existing functionality. Only add and improve features.",
            3: "Justified Removal: Removal of code is only permitted for unfixable errors or major architectural refactors that have been agreed upon by the team.",
            4: "Analyze First: Always analyze the latest work from other AIs in the shared channel before proposing new changes to avoid conflicts and build upon existing ideas.",
            5: "Log Everything: All significant suggestions, code generations, and analyses must be logged to the bridge for transparency."
        }
        self.logger = logging.getLogger('AIBridge')

    def validate_change(self, change_type: str, reason: str) -> bool:
        """Validates a proposed change against the core rules."""
        self.logger.info(f"Validating change: {change_type} | Reason: {reason}")
        if change_type.lower() == "remove" and "unfixable_error" not in reason.lower() and "refactor" not in reason.lower():
            self.logger.warning(f"Rule Violation Blocked: Removal of code without proper justification ('{reason}').")
            return False
        return True

    def display_rules(self):
        """Returns a string representation of the rules."""
        return "\n".join(f"Rule #{num}: {text}" for num, text in self.rules.items())


class EnhancedAIBridge:
    """
    Manages persistent, shared communication channels for multiple AI assistants.
    """

    def __init__(self):
        """Initializes the bridge, setting up directories, logging, and channels."""
        self.base_dir = Path.home() / '.gem' / 'ai_bridge'
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.logger = self._setup_logging()
        self.rules = GEMRules()

        self.channels: Dict[str, Path] = {
            'gemini': self.base_dir / 'gemini.json',
            'copilot': self.base_dir / 'copilot.json',
            'amazon_q': self.base_dir / 'amazon_q.json',
            'shared': self.base_dir / 'shared.json'
        }

        self._initialize_channels()
        self.logger.info("Enhanced AI Bridge initialized successfully.")
        self.logger.info("Guiding Principles:\n" + self.rules.display_rules())

    def _setup_logging(self) -> logging.Logger:
        """Configures a logger for the bridge's operations."""
        log_file = self.base_dir / 'bridge.log'
        logger = logging.getLogger('AIBridge')
        logger.setLevel(logging.INFO)

        # Avoid adding handlers if they already exist (e.g., in a REPL)
        if not logger.handlers:
            handler = logging.FileHandler(log_file, encoding='utf-8')
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def _initialize_channels(self):
        """Ensures all channel files exist and are valid JSON arrays."""
        for channel_path in self.channels.values():
            if not channel_path.exists() or channel_path.stat().st_size == 0:
                channel_path.write_text('[]', encoding='utf-8')

    def send_message(self, sender: str, content: str, recipients: Optional[List[str]] = None):
        """
        Sends a message from a sender to one or more recipients.
        The message is always logged to the sender's channel and the shared channel.
        """
        if sender not in self.channels:
            self.logger.error(f"Attempted to send from an unknown sender: {sender}")
            return

        timestamp = datetime.now().isoformat()
        message_data = {
            'timestamp': timestamp,
            'sender': sender,
            'content': content
        }

        # Log to the sender's own channel and the shared broadcast channel
        self._append_to_channel(self.channels[sender], message_data)
        self._append_to_channel(self.channels['shared'], message_data)

        # Log to specific recipient channels if provided
        if recipients:
            for recipient in recipients:
                if recipient in self.channels:
                    self._append_to_channel(self.channels[recipient], message_data)
                else:
                    self.logger.warning(f"Unknown recipient '{recipient}' specified.")

    def acknowledge_message(self, acknowledger: str, message_to_ack: Dict[str, Any]):
        """Creates and sends a formal acknowledgment message."""
        original_sender = message_to_ack.get('sender', 'unknown')
        original_timestamp = message_to_ack.get('timestamp', 'unknown_time')
        original_content_snip = message_to_ack.get('content', '')[:40]

        ack_content = f"Acknowledged and analyzed message from '{original_sender}' (sent at {original_timestamp}): '{original_content_snip}...'"
        self.send_message(sender=acknowledger, content=ack_content)

    def get_messages(self, channel_name: str = 'shared', last_n: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Retrieves messages from a specific channel (defaults to 'shared').
        """
        if channel_name not in self.channels:
            self.logger.error(f"Attempted to read from an unknown channel: {channel_name}")
            return []

        messages = self._read_channel(self.channels[channel_name])

        if last_n:
            return messages[-last_n:]
        return messages

    def _append_to_channel(self, channel_path: Path, message: Dict[str, Any]):
        """Safely appends a message to a JSON file channel."""
        try:
            # A file lock would be needed for true multi-process safety,
            # but for this use case, read-append-write is sufficient.
            messages = self._read_channel(channel_path)
            messages.append(message)
            channel_path.write_text(json.dumps(messages, indent=2, ensure_ascii=False), encoding='utf-8')
            self.logger.info(f"Message from '{message['sender']}' added to {channel_path.name}")
        except Exception as e:
            self.logger.error(f"Error writing to channel {channel_path.name}: {e}", exc_info=True)

    def _read_channel(self, channel_path: Path) -> List[Dict[str, Any]]:
        """Safely reads a list of messages from a JSON file channel."""
        try:
            return json.loads(channel_path.read_text(encoding='utf-8'))
        except (json.JSONDecodeError, FileNotFoundError):
            # If file is corrupted or missing, return an empty list and log it.
            self.logger.warning(f"Channel file {channel_path.name} was corrupted or not found. Resetting.")
            channel_path.write_text('[]', encoding='utf-8')
            return []