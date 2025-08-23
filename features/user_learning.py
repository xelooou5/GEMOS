#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
💎 GEM OS - User Learning System
Adaptive learning and personalization for accessibility
"""

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta

@dataclass
class UserPreference:
    """User preference data structure."""
    key: str
    value: Any
    confidence: float = 0.5
    last_updated: str = ""
    usage_count: int = 0

@dataclass
class InteractionPattern:
    """User interaction pattern."""
    command_type: str
    frequency: int
    success_rate: float
    avg_response_time: float
    preferred_phrasing: List[str]
    last_used: str

class UserLearningSystem:
    """Learns from user interactions to improve accessibility."""
    
    def __init__(self, gem_instance, logger: Optional[logging.Logger] = None):
        self.gem = gem_instance
        self.logger = logger or logging.getLogger("UserLearning")
        
        # Data storage
        self.data_dir = Path.home() / '.gem' / 'user_data'
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.preferences_file = self.data_dir / 'preferences.json'
        self.patterns_file = self.data_dir / 'interaction_patterns.json'
        self.context_file = self.data_dir / 'conversation_context.json'
        
        # Learning data
        self.user_preferences: Dict[str, UserPreference] = {}
        self.interaction_patterns: Dict[str, InteractionPattern] = {}
        self.conversation_history: List[Dict[str, Any]] = []
        
        # Learning parameters
        self.learning_rate = 0.1
        self.confidence_threshold = 0.7
        self.max_history = 1000
    
    async def initialize(self):
        """Initialize the learning system."""
        self.logger.info("Initializing User Learning System...")
        
        await self._load_user_data()
        
        # Start background learning tasks
        asyncio.create_task(self._periodic_analysis())
        
        self.logger.info("User Learning System initialized")
    
    async def _load_user_data(self):
        """Load existing user data."""
        try:
            # Load preferences
            if self.preferences_file.exists():
                with open(self.preferences_file, 'r') as f:
                    data = json.load(f)
                    self.user_preferences = {
                        k: UserPreference(**v) for k, v in data.items()
                    }
                self.logger.info(f"Loaded {len(self.user_preferences)} user preferences")
            
            # Load interaction patterns
            if self.patterns_file.exists():
                with open(self.patterns_file, 'r') as f:
                    data = json.load(f)
                    self.interaction_patterns = {
                        k: InteractionPattern(**v) for k, v in data.items()
                    }
                self.logger.info(f"Loaded {len(self.interaction_patterns)} interaction patterns")
            
            # Load conversation context
            if self.context_file.exists():
                with open(self.context_file, 'r') as f:
                    self.conversation_history = json.load(f)
                self.logger.info(f"Loaded {len(self.conversation_history)} conversation entries")
        
        except Exception as e:
            self.logger.error(f"Error loading user data: {e}")
    
    async def _save_user_data(self):
        """Save user data to files."""
        try:
            # Save preferences
            with open(self.preferences_file, 'w') as f:
                data = {k: asdict(v) for k, v in self.user_preferences.items()}
                json.dump(data, f, indent=2)
            
            # Save patterns
            with open(self.patterns_file, 'w') as f:
                data = {k: asdict(v) for k, v in self.interaction_patterns.items()}
                json.dump(data, f, indent=2)
            
            # Save conversation context (keep only recent)
            recent_history = self.conversation_history[-self.max_history:]
            with open(self.context_file, 'w') as f:
                json.dump(recent_history, f, indent=2)
            
            self.logger.debug("User data saved successfully")
        
        except Exception as e:
            self.logger.error(f"Error saving user data: {e}")
    
    async def learn_from_interaction(self, user_input: str, system_response: str, 
                                   success: bool, response_time: float):
        """Learn from a user interaction."""
        timestamp = datetime.now().isoformat()
        
        # Record interaction
        interaction = {
            'timestamp': timestamp,
            'user_input': user_input,
            'system_response': system_response,
            'success': success,
            'response_time': response_time
        }
        
        self.conversation_history.append(interaction)
        
        # Analyze and learn
        await self._analyze_interaction(interaction)
        
        # Update patterns
        await self._update_interaction_patterns(user_input, success, response_time)
        
        # Learn preferences
        await self._learn_preferences(user_input, success)
        
        # Save data periodically
        if len(self.conversation_history) % 10 == 0:
            await self._save_user_data()
    
    async def _analyze_interaction(self, interaction: Dict[str, Any]):
        """Analyze individual interaction for learning opportunities."""
        user_input = interaction['user_input'].lower()
        success = interaction['success']
        
        # Learn speech patterns
        if success:
            # User's preferred way of asking
            command_type = self._classify_command(user_input)
            if command_type:
                if command_type not in self.interaction_patterns:
                    self.interaction_patterns[command_type] = InteractionPattern(
                        command_type=command_type,
                        frequency=0,
                        success_rate=0.0,
                        avg_response_time=0.0,
                        preferred_phrasing=[],
                        last_used=""
                    )
                
                pattern = self.interaction_patterns[command_type]
                if user_input not in pattern.preferred_phrasing:
                    pattern.preferred_phrasing.append(user_input)
                    # Keep only top 5 phrasings
                    pattern.preferred_phrasing = pattern.preferred_phrasing[-5:]
        
        # Learn from failures
        if not success:
            await self._learn_from_failure(user_input)
    
    def _classify_command(self, user_input: str) -> Optional[str]:
        """Classify user input into command types."""
        input_lower = user_input.lower()
        
        # Time-related
        if any(word in input_lower for word in ['time', 'clock', 'hora', 'horas']):
            return 'time_query'
        
        # Help requests
        if any(word in input_lower for word in ['help', 'ajuda', 'assist']):
            return 'help_request'
        
        # Volume control
        if any(word in input_lower for word in ['volume', 'loud', 'quiet', 'som']):
            return 'volume_control'
        
        # Health related
        if any(word in input_lower for word in ['health', 'medicine', 'saúde', 'remédio']):
            return 'health_query'
        
        # Learning related
        if any(word in input_lower for word in ['learn', 'teach', 'study', 'aprender']):
            return 'learning_request'
        
        return 'general_query'
    
    async def _update_interaction_patterns(self, user_input: str, success: bool, response_time: float):
        """Update interaction patterns based on usage."""
        command_type = self._classify_command(user_input)
        if not command_type:
            return
        
        if command_type not in self.interaction_patterns:
            self.interaction_patterns[command_type] = InteractionPattern(
                command_type=command_type,
                frequency=0,
                success_rate=0.0,
                avg_response_time=0.0,
                preferred_phrasing=[],
                last_used=""
            )
        
        pattern = self.interaction_patterns[command_type]
        pattern.frequency += 1
        pattern.last_used = datetime.now().isoformat()
        
        # Update success rate (exponential moving average)
        if pattern.frequency == 1:
            pattern.success_rate = 1.0 if success else 0.0
        else:
            alpha = 0.1  # Learning rate
            pattern.success_rate = (1 - alpha) * pattern.success_rate + alpha * (1.0 if success else 0.0)
        
        # Update average response time
        if pattern.frequency == 1:
            pattern.avg_response_time = response_time
        else:
            alpha = 0.1
            pattern.avg_response_time = (1 - alpha) * pattern.avg_response_time + alpha * response_time
    
    async def _learn_preferences(self, user_input: str, success: bool):
        """Learn user preferences from interactions."""
        input_lower = user_input.lower()
        
        # Learn speech speed preference
        if 'slow' in input_lower or 'slower' in input_lower:
            await self._update_preference('speech_rate', 'slow', 0.8)
        elif 'fast' in input_lower or 'faster' in input_lower:
            await self._update_preference('speech_rate', 'fast', 0.8)
        
        # Learn verbosity preference
        if any(word in input_lower for word in ['brief', 'short', 'quick']):
            await self._update_preference('response_style', 'brief', 0.7)
        elif any(word in input_lower for word in ['detailed', 'explain', 'more']):
            await self._update_preference('response_style', 'detailed', 0.7)
        
        # Learn language preference
        portuguese_words = ['português', 'brasileiro', 'brasil']
        english_words = ['english', 'inglês']
        
        if any(word in input_lower for word in portuguese_words):
            await self._update_preference('language', 'pt-BR', 0.9)
        elif any(word in input_lower for word in english_words):
            await self._update_preference('language', 'en-US', 0.9)
    
    async def _update_preference(self, key: str, value: Any, confidence: float):
        """Update a user preference."""
        timestamp = datetime.now().isoformat()
        
        if key in self.user_preferences:
            pref = self.user_preferences[key]
            # Update with weighted average
            old_weight = pref.confidence * pref.usage_count
            new_weight = confidence
            total_weight = old_weight + new_weight
            
            if total_weight > 0:
                pref.confidence = total_weight / (pref.usage_count + 1)
            pref.usage_count += 1
            pref.last_updated = timestamp
            
            # Update value if confidence is high enough
            if confidence > pref.confidence:
                pref.value = value
        else:
            self.user_preferences[key] = UserPreference(
                key=key,
                value=value,
                confidence=confidence,
                last_updated=timestamp,
                usage_count=1
            )
        
        self.logger.info(f"Updated preference: {key} = {value} (confidence: {confidence:.2f})")
    
    async def _learn_from_failure(self, user_input: str):
        """Learn from failed interactions."""
        # Analyze what might have gone wrong
        input_lower = user_input.lower()
        
        # If user seems frustrated
        frustration_words = ['again', 'repeat', 'understand', 'wrong', 'no']
        if any(word in input_lower for word in frustration_words):
            # Suggest slower speech
            await self._update_preference('speech_rate', 'slow', 0.6)
            # Suggest more detailed responses
            await self._update_preference('response_style', 'detailed', 0.6)
    
    async def get_personalized_response(self, base_response: str) -> str:
        """Personalize response based on learned preferences."""
        response = base_response
        
        # Apply speech style preferences
        if 'response_style' in self.user_preferences:
            style_pref = self.user_preferences['response_style']
            if style_pref.confidence > self.confidence_threshold:
                if style_pref.value == 'brief':
                    # Make response more concise
                    sentences = response.split('.')
                    response = sentences[0] + '.' if sentences else response
                elif style_pref.value == 'detailed':
                    # Add helpful context
                    response += " Let me know if you need more information or help with anything else."
        
        return response
    
    async def get_suggested_commands(self) -> List[str]:
        """Get suggested commands based on user patterns."""
        suggestions = []
        
        # Sort patterns by frequency and success rate
        sorted_patterns = sorted(
            self.interaction_patterns.values(),
            key=lambda p: p.frequency * p.success_rate,
            reverse=True
        )
        
        for pattern in sorted_patterns[:5]:  # Top 5
            if pattern.preferred_phrasing:
                suggestions.append(pattern.preferred_phrasing[-1])  # Most recent phrasing
        
        return suggestions
    
    async def _periodic_analysis(self):
        """Periodic analysis of user data."""
        while True:
            try:
                await asyncio.sleep(300)  # Every 5 minutes
                
                # Analyze recent interactions
                recent_interactions = self.conversation_history[-50:]  # Last 50
                
                if len(recent_interactions) >= 10:
                    success_rate = sum(1 for i in recent_interactions if i['success']) / len(recent_interactions)
                    avg_response_time = sum(i['response_time'] for i in recent_interactions) / len(recent_interactions)
                    
                    self.logger.info(f"Recent performance: {success_rate:.2f} success rate, {avg_response_time:.2f}s avg response time")
                    
                    # Adjust system based on performance
                    if success_rate < 0.7:
                        # System struggling, suggest slower speech
                        await self._update_preference('speech_rate', 'slow', 0.5)
                        await self._update_preference('response_style', 'detailed', 0.5)
                
                # Save data
                await self._save_user_data()
                
            except Exception as e:
                self.logger.error(f"Error in periodic analysis: {e}")
    
    def get_user_stats(self) -> Dict[str, Any]:
        """Get user interaction statistics."""
        total_interactions = len(self.conversation_history)
        if total_interactions == 0:
            return {"total_interactions": 0}
        
        successful_interactions = sum(1 for i in self.conversation_history if i['success'])
        success_rate = successful_interactions / total_interactions
        
        avg_response_time = sum(i['response_time'] for i in self.conversation_history) / total_interactions
        
        # Most used commands
        command_usage = {}
        for interaction in self.conversation_history:
            cmd_type = self._classify_command(interaction['user_input'])
            if cmd_type:
                command_usage[cmd_type] = command_usage.get(cmd_type, 0) + 1
        
        most_used = sorted(command_usage.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            "total_interactions": total_interactions,
            "success_rate": success_rate,
            "avg_response_time": avg_response_time,
            "most_used_commands": most_used,
            "learned_preferences": len(self.user_preferences),
            "interaction_patterns": len(self.interaction_patterns)
        }
    
    def shutdown(self):
        """Shutdown the learning system."""
        asyncio.create_task(self._save_user_data())
        self.logger.info("User Learning System shutdown")