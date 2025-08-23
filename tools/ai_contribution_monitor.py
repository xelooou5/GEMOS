#!/usr/bin/env python3
"""
💎 GEM OS - AI Contribution Monitor
Enhanced monitoring system to capture and implement AI partner contributions
Following Rule #4: Always analyze what other AI partners did first
"""

import asyncio
import json
import time
from pathlib import Path
from typing import Dict, List, Any
import logging

class AIContributionMonitor:
    """Monitor and process AI partner contributions in real-time"""
    
    def __init__(self):
        self.bridge_dir = Path.home() / '.gem' / 'ai_bridge'
        self.contributions_dir = Path.home() / '.gem' / 'ai_contributions'
        self.contributions_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = logging.getLogger('AIContributionMonitor')
        self.last_check = {}
        self.processed_contributions = set()
        
    async def start_monitoring(self):
        """Start monitoring for new AI contributions"""
        self.logger.info("🔍 Starting AI contribution monitoring...")
        
        while True:
            try:
                await self._check_for_new_contributions()
                await asyncio.sleep(5)  # Check every 5 seconds
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(10)
    
    async def _check_for_new_contributions(self):
        """Check for new contributions from AI partners"""
        for ai_file in self.bridge_dir.glob('*.json'):
            if ai_file.name in ['shared.json']:
                continue
                
            try:
                current_size = ai_file.stat().st_size
                last_size = self.last_check.get(ai_file.name, 0)
                
                if current_size > last_size:
                    await self._process_new_messages(ai_file)
                    self.last_check[ai_file.name] = current_size
                    
            except Exception as e:
                self.logger.error(f"Error checking {ai_file}: {e}")
    
    async def _process_new_messages(self, ai_file: Path):
        """Process new messages from AI partners"""
        try:
            with open(ai_file, 'r') as f:
                messages = json.load(f)
            
            ai_name = ai_file.stem
            
            # Check last few messages for code contributions
            recent_messages = messages[-5:] if len(messages) >= 5 else messages
            
            for msg in recent_messages:
                msg_id = f"{ai_name}_{msg['timestamp']}"
                
                if msg_id not in self.processed_contributions:
                    await self._analyze_message_for_code(ai_name, msg)
                    self.processed_contributions.add(msg_id)
                    
        except Exception as e:
            self.logger.error(f"Error processing messages from {ai_file}: {e}")
    
    async def _analyze_message_for_code(self, ai_name: str, message: Dict[str, Any]):
        """Analyze message for code contributions"""
        content = message.get('content', '').lower()
        
        # Look for code indicators
        code_indicators = [
            'def ', 'class ', 'import ', 'from ',
            '```python', '```', 'implement', 'code',
            'function', 'method', 'module'
        ]
        
        if any(indicator in content for indicator in code_indicators):
            self.logger.info(f"🔍 Potential code contribution detected from {ai_name}")
            await self._save_contribution(ai_name, message)
            await self._notify_integration_needed(ai_name, message)
    
    async def _save_contribution(self, ai_name: str, message: Dict[str, Any]):
        """Save contribution for analysis"""
        timestamp = message['timestamp']
        filename = f"{ai_name}_{timestamp.replace(':', '-')}.json"
        filepath = self.contributions_dir / filename
        
        contribution_data = {
            'ai_name': ai_name,
            'timestamp': timestamp,
            'content': message['content'],
            'processed': False,
            'integration_status': 'pending'
        }
        
        with open(filepath, 'w') as f:
            json.dump(contribution_data, f, indent=2)
        
        self.logger.info(f"💾 Saved contribution from {ai_name}: {filename}")
    
    async def _notify_integration_needed(self, ai_name: str, message: Dict[str, Any]):
        """Notify that integration is needed"""
        self.logger.info(f"🚀 INTEGRATION NEEDED: New code from {ai_name}")
        
        # Create integration task
        integration_file = self.contributions_dir / 'integration_queue.json'
        
        try:
            if integration_file.exists():
                with open(integration_file, 'r') as f:
                    queue = json.load(f)
            else:
                queue = []
            
            queue.append({
                'ai_name': ai_name,
                'timestamp': message['timestamp'],
                'content_preview': message['content'][:200] + '...',
                'status': 'pending',
                'priority': 'high' if 'urgent' in message['content'].lower() else 'normal'
            })
            
            with open(integration_file, 'w') as f:
                json.dump(queue, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Error updating integration queue: {e}")
    
    def get_pending_contributions(self) -> List[Dict[str, Any]]:
        """Get list of pending contributions"""
        contributions = []
        
        for contrib_file in self.contributions_dir.glob('*.json'):
            if contrib_file.name == 'integration_queue.json':
                continue
                
            try:
                with open(contrib_file, 'r') as f:
                    contrib_data = json.load(f)
                
                if not contrib_data.get('processed', False):
                    contributions.append(contrib_data)
                    
            except Exception as e:
                self.logger.error(f"Error reading contribution {contrib_file}: {e}")
        
        return sorted(contributions, key=lambda x: x['timestamp'])

if __name__ == "__main__":
    print("🔍 AI Contribution Monitor - Following Rule #4")
    print("Ready to capture and implement new codes from Copilot and Gemini")