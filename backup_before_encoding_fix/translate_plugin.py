#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🌐 GEM OS - Translate Plugin (plugins/translate_plugin.py)

Provides text translation between languages.
Registers commands with PluginManager:
- "translate:text"
"""

from __future__ import annotations

try:
    from deep_translator import GoogleTranslator
except ImportError:
    GoogleTranslator = None


def translate_text(text: str, src: str = "auto", dest: str = "en") -> str:
    """Translate text from source language to target language."""
    if GoogleTranslator is None:
        return f"🌐 (offline) {text} -> ({dest}) {text}"

    try:
        translated = GoogleTranslator(source=src, target=dest).translate(text)
        return f"🌐 {src}->{dest}: {translated}"
    except Exception as e:
        return f"⚠️ Translation failed: {e}"


def register(plugin_manager):
    """Register plugin commands."""
    plugin_manager.register_command("translate:text", translate_text)
