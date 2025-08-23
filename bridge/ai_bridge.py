#!/usr/bin/env python3
"""
Enhanced AI Bridge - Copilot's improved collaboration system
"""

import os
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

class AIBridge:
    def __init__(self):
        self.shared_dir = Path.home() / '.ai_shared'
        self.shared_dir.mkdir(exist_ok=True)
        
        # Files for each AI assistant
        self.files = {
            'conversations': self.shared_dir / 'conversations.json',
            'gemini': self.shared_dir / 'gemini_chat.json',
            'copilot': self.shared_dir / 'copilot_chat.json',
            'amazon_q': self.shared_dir / 'amazon_q_chat.json',
            'current_context': self.shared_dir / 'current_context.json'
        }
        
        self._initialize_files()

    def _initialize_files(self):
        """Initialize all required files"""
        for file in self.files.values():
            if not file.exists():
                file.write_text('[]')

    def log_message(self, ai_name: str, message: Dict[str, Any]):
        """Log a message from an AI assistant"""
        file = self.files.get(ai_name.lower())
        if file:
            messages = self._read_json(file)
            messages.append({
                'timestamp': datetime.now().isoformat(),
                'content': message
            })
            self._write_json(file, messages)

    def get_messages(self, ai_name: str = None) -> list:
        """Get messages from specific AI or all if none specified"""
        if ai_name:
            file = self.files.get(ai_name.lower())
            return self._read_json(file) if file else []
        
        all_messages = []
        for name, file in self.files.items():
            if name != 'current_context':
                messages = self._read_json(file)
                all_messages.extend([{**m, 'source': name} for m in messages])
        return sorted(all_messages, key=lambda x: x['timestamp'])

    def update_context(self, context: Dict[str, Any]):
        """Update the current context for all AIs"""
        self._write_json(self.files['current_context'], context)

    def _read_json(self, file: Path) -> list:
        try:
            return json.loads(file.read_text())
        except:
            return []

    def _write_json(self, file: Path, data: Any):
        file.write_text(json.dumps(data, indent=2))