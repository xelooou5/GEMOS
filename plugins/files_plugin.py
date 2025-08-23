#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
üìÇ GEM OS - Files Plugin (plugins/files_plugin.py)

Provides file management commands.
Registers commands with PluginManager:
- "file:list"
- "file:read"
- "file:write"
"""

from __future__ import annotations
import os
from pathlib import Path

# Restrict operations to safe dirs
SAFE_DIRS = ["data", "book_library"]


def is_safe_path(path: str) -> bool:
    """Ensure file operations stay inside SAFE_DIRS."""
    return any(Path(path).resolve().is_relative_to(Path(s).resolve()) for s in SAFE_DIRS)


def list_files(directory: str = "data") -> str:
    """List files in a directory (restricted)."""
    if not is_safe_path(directory):
        return "‚ùå Access denied."
    try:
        files = os.listdir(directory)
        return f"üìÇ Files in {directory}:\n" + "\n".join(files)
    except Exception as e:
        return f"‚ö†Ô∏è Error listing files: {e}"


def read_file(filepath: str) -> str:
    """Read text content from a file (restricted)."""
    if not is_safe_path(filepath):
        return "‚ùå Access denied."
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f"üìñ {filepath}:\n{f.read(500)}..."
    except Exception as e:
        return f"‚ö†Ô∏è Error reading {filepath}: {e}"


def write_file(filepath: str, content: str, mode: str = "w") -> str:
    """Write or append text to a file (restricted)."""
    if not is_safe_path(filepath):
        return "‚ùå Access denied."
    try:
        with open(filepath, mode, encoding="utf-8") as f:
            f.write(content + "\n")
        return f"‚úÖ Written to {filepath}"
    except Exception as e:
        return f"‚ö†Ô∏è Error writing {filepath}: {e}"


def register(plugin_manager):
    """Register plugin commands."""
    plugin_manager.register_command("file:list", list_files)
    plugin_manager.register_command("file:read", read_file)
    plugin_manager.register_command("file:write", write_file)
