#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
💎 GEM OS - Core Package
Core system components for accessibility-focused voice assistant
"""

from .audio_system import AudioSystem
from .config_manager import GEMConfigManager, GEMConfig
from .stt_module import STTModule
from .tts_module import TTSModule
from .llm_handler import LLMHandler
from .command_executor import CommandExecutor
from .system_monitor import SystemMonitor

__all__ = [
    'AudioSystem',
    'GEMConfigManager',
    'GEMConfig',
    'STTModule',
    'TTSModule',
    'LLMHandler',
    'CommandExecutor',
    'SystemMonitor'
]

__version__ = "2.0.0"
__author__ = "GEM Project"
__description__ = "Core components for GEM OS accessibility voice assistant"