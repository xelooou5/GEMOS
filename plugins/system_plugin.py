#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ðŸ’» GEM OS - System Plugin (plugins/system_plugin.py)

Provides basic system info commands.
Registers commands with PluginManager:
- "system:time"
- "system:date"
- "system:uptime"
- "system:info"
"""

from __future__ import annotations
import datetime
import platform

try:
    import psutil
except ImportError:
    psutil = None


def get_time() -> str:
    """Return current time."""
    return f"ðŸ•’ Current Time: {datetime.datetime.now().strftime('%H:%M:%S')}"


def get_date() -> str:
    """Return current date."""
    return f"ðŸ“… Current Date: {datetime.datetime.now().strftime('%Y-%m-%d')}"


def get_uptime() -> str:
    """Return system uptime."""
    if psutil:
        boot_time = datetime.datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.datetime.now() - boot_time
        return f"â�³ Uptime: {uptime}"
    return "â�³ Uptime not available (psutil missing)."


def get_system_info() -> str:
    """Return platform info."""
    return (
        f"ðŸ’» System Info:\n"
        f"- OS: {platform.system()} {platform.release()}\n"
        f"- Version: {platform.version()}\n"
        f"- Machine: {platform.machine()}\n"
        f"- Processor: {platform.processor()}"
    )


def register(plugin_manager):
    """Register plugin commands."""
    plugin_manager.register_command("system:time", get_time)
    plugin_manager.register_command("system:date", get_date)
    plugin_manager.register_command("system:uptime", get_uptime)
    plugin_manager.register_command("system:info", get_system_info)
