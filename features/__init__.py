#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
💎 GEM OS - Features Package
Feature modules for accessibility, health, learning, and productivity
"""

from .accessibility_tools import AccessibilityTools
from .health_assistant import HealthAssistant
from .learning_tools import LearningTools
from .productivity_tools import ProductivityTools

__all__ = [
    'AccessibilityTools',
    'HealthAssistant', 
    'LearningTools',
    'ProductivityTools'
]

__version__ = "2.0.0"
__author__ = "GEM Project"
__description__ = "Feature modules for GEM OS accessibility voice assistant"