#!/usr/bin/env python3
"""
Collaboration Manager - Central coordination for AI collaboration
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from .real_time_collaboration import RealTimeCollaboration
from .context_sharing import ContextSharingSystem

class CollaborationManager:
    """Central manager for AI collaboration features"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.real_time_collab = RealTimeCollaboration(logger)
        self.context_sharing = ContextSharingSystem(logger)
        self.is_active = False
        
    async def initialize(self):
        """Initialize collaboration systems"""
        try:
            await self.real_time_collab.start_collaboration()
            self.is_active = True
            self.logger.info("🤝 AI Collaboration Manager initialized")
            
            # Share initial GEM OS context
            initial_context = {
                'status': 'running',
                'features': [
                    'AI Companion with Emotional Intelligence',
                    'Advanced Accessibility System',
                    'Smart Health Monitoring',
                    'Multi-AI Collaboration',
                    'Real-time AI Bridge'
                ],
                'current_focus': 'AI Collaboration Enhancement',
                'available_for_collaboration': True
            }
            
            self.context_sharing.update_gem_context(initial_context)
            
        except Exception as e:
            self.logger.error(f"Error initializing collaboration manager: {e}")
    
    def share_implementation_context(self, implementation: Dict[str, Any]):
        """Share implementation context with other AIs"""
        if self.is_active:
            self.context_sharing.share_code_context({
                'type': 'implementation',
                'title': implementation.get('title', 'Code Implementation'),
                'description': implementation.get('description', ''),
                'status': implementation.get('status', 'completed'),
                'author': 'amazon_q',
                'integration_point': implementation.get('module', 'unknown')
            })
    
    def update_gem_status(self, status_update: Dict[str, Any]):
        """Update GEM OS status for collaboration"""
        if self.is_active:
            self.context_sharing.update_gem_context(status_update)
    
    def get_collaboration_insights(self) -> Dict[str, Any]:
        """Get insights about current collaboration"""
        if not self.is_active:
            return {'status': 'inactive'}
            
        return self.context_sharing.get_collaboration_context()
    
    def shutdown(self):
        """Shutdown collaboration systems"""
        if self.is_active:
            self.real_time_collab.stop_collaboration()
            self.is_active = False
            self.logger.info("🛑 AI Collaboration Manager shutdown")