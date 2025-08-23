#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ðŸ˜‚ GEM OS - Jokes Plugin (plugins/jokes_plugin.py)

Provides random jokes for entertainment.
Registers commands with PluginManager:
- "joke:get"
"""

from __future__ import annotations

try:
    import pyjokes
except ImportError:
    pyjokes = None

import random


FALLBACK_JOKES = [
    "Por que os programadores sempre confudem Halloween e Natal? Porque OCT 31 == DEC 25.",
    "Qual Ã© o animal preferido dos programadores? O bug ðŸ�ž.",
    "Como o programador se despede? 'AtÃ© o prÃ³ximo loop!'",
]


def get_joke(category: str = "neutral") -> str:
    """Return a random joke, optionally filtered by category."""
    if pyjokes:
        try:
            return f"ðŸ˜‚ {pyjokes.get_joke(category=category)}"
        except Exception:
            return f"ðŸ˜‚ {pyjokes.get_joke()}"
    return f"ðŸ˜‚ {random.choice(FALLBACK_JOKES)}"


def register(plugin_manager):
    """Register plugin commands."""
    plugin_manager.register_command("joke:get", get_joke)
