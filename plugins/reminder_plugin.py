#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
⏰ GEM OS - Reminder Plugin (plugins/reminder_plugin.py)

Allows creating and listing reminders.
Registers commands with PluginManager:
- "reminder:add"
- "reminder:list"
"""

from __future__ import annotations
import datetime
from typing import Optional, List, Dict


REMINDERS: List[Dict] = []


def add_reminder(text: str, minutes_from_now: int = 1) -> str:
    """Add a reminder that should trigger in X minutes."""
    remind_time = datetime.datetime.now() + datetime.timedelta(minutes=minutes_from_now)
    reminder = {"text": text, "time": remind_time}
    REMINDERS.append(reminder)
    return f"⏰ Reminder set: '{text}' at {remind_time.strftime('%H:%M:%S')}"


def list_reminders() -> str:
    """List all active reminders."""
    if not REMINDERS:
        return "⏰ No active reminders."
    formatted = "\n".join([f"- {r['text']} at {r['time'].strftime('%H:%M:%S')}" for r in REMINDERS])
    return f"⏰ Active Reminders:\n{formatted}"


def register(plugin_manager):
