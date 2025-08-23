#!/usr/bin/env python3
"""
Real-time AI Collaboration - Copilot's enhanced collaboration system
"""

import asyncio
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

class RealTimeCollaboration:
    """Real-time collaboration system for multiple AIs"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.bridge_dir = Path.home() / '.gem' / 'ai_bridge'
        self.active_sessions = {}
        self.collaboration_queue = asyncio.Queue()
        self.is_running = False
        
    async def start_collaboration(self):
        """Start real-time collaboration monitoring"""
        self.is_running = True
        self.logger.info("🤝 Real-time AI collaboration started")
        
        # Start background tasks
        asyncio.create_task(self._monitor_ai_messages())
        asyncio.create_task(self._process_collaboration_queue())
        
    async def _monitor_ai_messages(self):
        """Monitor AI bridge for new messages"""
        last_check = {}
        
        while self.is_running:
            try:
                for ai_file in self.bridge_dir.glob('*.json'):
                    if ai_file.name == 'shared.json':
                        continue
                        
                    current_size = ai_file.stat().st_size
                    if ai_file.name not in last_check or last_check[ai_file.name] != current_size:
                        await self._process_new_messages(ai_file)
                        last_check[ai_file.name] = current_size
                        
            except Exception as e:
                self.logger.error(f"Error monitoring AI messages: {e}")
                
            await asyncio.sleep(2)
    
    async def _process_new_messages(self, ai_file: Path):
        """Process new messages from AI"""
        try:
            with open(ai_file, 'r') as f:
                messages = json.load(f)
                
            if messages:
                latest_message = messages[-1]
                await self.collaboration_queue.put({
                    'type': 'new_message',
                    'ai': ai_file.stem,
                    'message': latest_message
                })
                
        except Exception as e:
            self.logger.error(f"Error processing messages from {ai_file}: {e}")
    
    async def _process_collaboration_queue(self):
        """Process collaboration events"""
        while self.is_running:
            try:
                event = await asyncio.wait_for(self.collaboration_queue.get(), timeout=1.0)
                await self._handle_collaboration_event(event)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.logger.error(f"Error processing collaboration queue: {e}")
    
    async def _handle_collaboration_event(self, event: Dict[str, Any]):
        """Handle collaboration events"""
        if event['type'] == 'new_message':
            ai_name = event['ai']
            message = event['message']
            
            # Check if message contains code or suggestions
            content = message.get('content', '')
            if any(keyword in content.lower() for keyword in ['code', 'implement', 'suggestion', 'feature']):
                self.logger.info(f"🔄 Collaboration opportunity detected from {ai_name}")
                await self._notify_other_ais(ai_name, message)
    
    async def _notify_other_ais(self, sender: str, message: Dict[str, Any]):
        """Notify other AIs about collaboration opportunities"""
        notification = {
            'type': 'collaboration_notification',
            'from': sender,
            'content': message['content'][:200] + '...' if len(message['content']) > 200 else message['content'],
            'timestamp': time.time()
        }
        
        # Log to shared collaboration file
        collab_file = self.bridge_dir / 'collaboration_events.json'
        try:
            if collab_file.exists():
                with open(collab_file, 'r') as f:
                    events = json.load(f)
            else:
                events = []
                
            events.append(notification)
            events = events[-50:]  # Keep last 50 events
            
            with open(collab_file, 'w') as f:
                json.dump(events, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Error logging collaboration event: {e}")
    
    def stop_collaboration(self):
        """Stop real-time collaboration"""
        self.is_running = False
        self.logger.info("🛑 Real-time AI collaboration stopped")