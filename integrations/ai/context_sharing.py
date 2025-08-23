#!/usr/bin/env python3
"""
Context Sharing System - Enhanced context sharing for AI collaboration
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

class ContextSharingSystem:
    """Advanced context sharing system for AI collaboration"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.bridge_dir = Path.home() / '.gem' / 'ai_bridge'
        self.context_file = self.bridge_dir / 'shared_context.json'
        
    def update_gem_context(self, context: Dict[str, Any]):
        """Update GEM OS context for all AIs"""
        try:
            current_context = self._load_context()
            
            # Update with new context
            current_context.update({
                'gem_os': context,
                'last_updated': time.time(),
                'updated_by': 'amazon_q'
            })
            
            self._save_context(current_context)
            self.logger.info("📊 GEM OS context updated for AI collaboration")
            
        except Exception as e:
            self.logger.error(f"Error updating GEM context: {e}")
    
    def share_code_context(self, code_info: Dict[str, Any]):
        """Share code context between AIs"""
        try:
            current_context = self._load_context()
            
            if 'code_sharing' not in current_context:
                current_context['code_sharing'] = []
            
            code_entry = {
                'timestamp': time.time(),
                'info': code_info,
                'shared_by': code_info.get('author', 'unknown')
            }
            
            current_context['code_sharing'].append(code_entry)
            current_context['code_sharing'] = current_context['code_sharing'][-20:]  # Keep last 20
            
            self._save_context(current_context)
            self.logger.info(f"💻 Code context shared: {code_info.get('title', 'Untitled')}")
            
        except Exception as e:
            self.logger.error(f"Error sharing code context: {e}")
    
    def get_collaboration_context(self) -> Dict[str, Any]:
        """Get current collaboration context"""
        try:
            context = self._load_context()
            
            # Add recent activity summary
            context['activity_summary'] = self._generate_activity_summary()
            
            return context
            
        except Exception as e:
            self.logger.error(f"Error getting collaboration context: {e}")
            return {}
    
    def _generate_activity_summary(self) -> Dict[str, Any]:
        """Generate activity summary from AI messages"""
        try:
            summary = {
                'total_messages': 0,
                'active_ais': [],
                'recent_topics': [],
                'last_activity': None
            }
            
            # Analyze shared messages
            shared_file = self.bridge_dir / 'shared.json'
            if shared_file.exists():
                with open(shared_file, 'r') as f:
                    messages = json.load(f)
                
                summary['total_messages'] = len(messages)
                summary['active_ais'] = list(set(msg['sender'] for msg in messages))
                
                if messages:
                    summary['last_activity'] = messages[-1]['timestamp']
                    
                    # Extract topics from recent messages
                    recent_messages = messages[-10:]
                    topics = []
                    for msg in recent_messages:
                        content = msg['content'].lower()
                        if 'gem os' in content:
                            topics.append('GEM OS Development')
                        if 'code' in content or 'implement' in content:
                            topics.append('Code Implementation')
                        if 'collaboration' in content:
                            topics.append('AI Collaboration')
                    
                    summary['recent_topics'] = list(set(topics))
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error generating activity summary: {e}")
            return {}
    
    def _load_context(self) -> Dict[str, Any]:
        """Load shared context"""
        try:
            if self.context_file.exists():
                with open(self.context_file, 'r') as f:
                    return json.load(f)
            return {}
        except:
            return {}
    
    def _save_context(self, context: Dict[str, Any]):
        """Save shared context"""
        try:
            with open(self.context_file, 'w') as f:
                json.dump(context, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving context: {e}")