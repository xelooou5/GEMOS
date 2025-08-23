#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GEM OS - Engines Package
Specialized processing engines for advanced functionality
"""

__version__ = "2.0.0"
__author__ = "GEM Project"

# Engine modules
from .transcription_engine import TranscriptionEngine
from .voice_training import VoiceTrainer
from .wake_word_trainer import WakeWordTrainer

__all__ = [
    "TranscriptionEngine",
    "VoiceTrainer",
    "WakeWordTrainer"
]