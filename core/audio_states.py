#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
💎 GEM OS - Audio System States
State machine pattern for AudioSystem clarity and management.
Implementing Copilot's suggestion with Gemini's state machine design.
"""

from enum import Enum, auto
from dataclasses import dataclass
from typing import Optional, Dict, Any
import time
import logging

class AudioState(Enum):
    """Audio system states for clear state management."""
    IDLE = auto()
    LISTENING = auto()
    PROCESSING = auto()
    SPEAKING = auto()
    WAKE_WORD_DETECTION = auto()
    ERROR = auto()
    SHUTDOWN = auto()

@dataclass
class AudioStateData:
    """Data associated with audio states."""
    current_state: AudioState = AudioState.IDLE
    previous_state: Optional[AudioState] = None
    state_start_time: float = 0.0
    error_message: Optional[str] = None
    context: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.context is None:
            self.context = {}
        if self.state_start_time == 0.0:
            self.state_start_time = time.time()

class AudioStateMachine:
    """State machine for managing audio system states."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.state_data = AudioStateData()
        self.state_history = []
        self.max_history = 50
        
        # Valid state transitions
        self.valid_transitions = {
            AudioState.IDLE: [AudioState.LISTENING, AudioState.WAKE_WORD_DETECTION, AudioState.SHUTDOWN],
            AudioState.LISTENING: [AudioState.PROCESSING, AudioState.IDLE, AudioState.ERROR, AudioState.SHUTDOWN],
            AudioState.PROCESSING: [AudioState.SPEAKING, AudioState.IDLE, AudioState.ERROR, AudioState.SHUTDOWN],
            AudioState.SPEAKING: [AudioState.IDLE, AudioState.LISTENING, AudioState.ERROR, AudioState.SHUTDOWN],
            AudioState.WAKE_WORD_DETECTION: [AudioState.LISTENING, AudioState.IDLE, AudioState.ERROR, AudioState.SHUTDOWN],
            AudioState.ERROR: [AudioState.IDLE, AudioState.SHUTDOWN],
            AudioState.SHUTDOWN: []  # Terminal state
        }
    
    def transition_to(self, new_state: AudioState, context: Dict[str, Any] = None, error_message: str = None) -> bool:
        """Transition to a new state with validation."""
        current_state = self.state_data.current_state
        
        # Validate transition
        if new_state not in self.valid_transitions.get(current_state, []):
            self.logger.warning(f"Invalid state transition from {current_state.name} to {new_state.name}")
            return False
        
        # Record state history
        self._record_state_change(current_state, new_state)
        
        # Update state data
        self.state_data.previous_state = current_state
        self.state_data.current_state = new_state
        self.state_data.state_start_time = time.time()
        self.state_data.error_message = error_message
        
        if context:
            self.state_data.context.update(context)
        
        self.logger.info(f"Audio state transition: {current_state.name} → {new_state.name}")
        
        # Execute state entry actions
        self._on_state_entry(new_state)
        
        return True
    
    def _record_state_change(self, from_state: AudioState, to_state: AudioState):
        """Record state change in history."""
        self.state_history.append({
            'from': from_state,
            'to': to_state,
            'timestamp': time.time(),
            'duration': time.time() - self.state_data.state_start_time
        })
        
        # Keep history manageable
        if len(self.state_history) > self.max_history:
            self.state_history = self.state_history[-self.max_history:]
    
    def _on_state_entry(self, state: AudioState):
        """Execute actions when entering a state."""
        if state == AudioState.IDLE:
            self.state_data.context.clear()
            self.state_data.error_message = None
        elif state == AudioState.ERROR:
            self.logger.error(f"Audio system entered error state: {self.state_data.error_message}")
        elif state == AudioState.SHUTDOWN:
            self.logger.info("Audio system shutting down")
    
    def get_current_state(self) -> AudioState:
        """Get current audio state."""
        return self.state_data.current_state
    
    def get_state_duration(self) -> float:
        """Get how long we've been in current state."""
        return time.time() - self.state_data.state_start_time
    
    def is_in_state(self, state: AudioState) -> bool:
        """Check if currently in specified state."""
        return self.state_data.current_state == state
    
    def can_transition_to(self, state: AudioState) -> bool:
        """Check if transition to state is valid."""
        return state in self.valid_transitions.get(self.state_data.current_state, [])
    
    def get_state_info(self) -> Dict[str, Any]:
        """Get comprehensive state information."""
        return {
            'current_state': self.state_data.current_state.name,
            'previous_state': self.state_data.previous_state.name if self.state_data.previous_state else None,
            'duration': self.get_state_duration(),
            'error_message': self.state_data.error_message,
            'context': self.state_data.context.copy(),
            'valid_transitions': [s.name for s in self.valid_transitions.get(self.state_data.current_state, [])]
        }
    
    def reset_to_idle(self):
        """Reset state machine to idle state."""
        self.transition_to(AudioState.IDLE, context={'reset': True})