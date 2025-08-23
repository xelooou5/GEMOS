#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ğŸ“š GEM OS - Wikipedia Plugin (plugins/wikipedia_plugin.py)

Provides quick summaries from Wikipedia.
Registers commands with PluginManager:
- "wiki:search"
"""

from __future__ import annotations
import wikipedia

# configure Wikipedia language
wikipedia.set_lang("pt")


def wiki_search(query: str, sentences: int = 2) -> str:
    """Fetch a short Wikipedia summary for a query."""
    try:
        summary = wikipedia.summary(query, sentences=sentences)
        return f"ğŸ“š {query}: {summary}"
    except wikipedia.exceptions.DisambiguationError as e:
        return f"â�Œ The query '{query}' is ambiguous. Options: {', '.join(e.options[:5])}"
    except wikipedia.exceptions.PageError:
        return f"â�Œ No results found for '{query}'."
    except Exception as e:
        return f"âš ï¸� Error fetching Wikipedia data: {e}"


def register(plugin_manager):
    """Register plugin commands."""
    plugin_manager.register_command("wiki:search", wiki_search)
