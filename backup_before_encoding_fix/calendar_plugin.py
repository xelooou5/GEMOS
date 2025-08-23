#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📅 GEM OS - Calendar Plugin (plugins/calendar_plugin.py)

Provides basic calendar and event management.
Registers commands with PluginManager:
- "calendar:add"
- "calendar:list"
- "calendar:remove"
"""

from __future__ import annotations
import json
import os
import datetime
from typing import List, Dict

EVENTS_FILE = "data/calendar_events.json"


def _load_events() -> List[Dict]:
    if not os.path.exists(EVENTS_FILE):
        return []
    try:
        with open(EVENTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save_events(events: List[Dict]) -> None:
    os.makedirs(os.path.dirname(EVENTS_FILE), exist_ok=True)
    with open(EVENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(events, f, indent=2, ensure_ascii=False)


def add_event(title: str, date: str, time: str = "00:00") -> str:
    """Add a new event to the calendar."""
    events = _load_events()
    new_event = {"title": title, "date": date, "time": time}
    events.append(new_event)
    _save_events(events)
    return f"✅ Evento adicionado: {title} em {date} às {time}"


def list_events() -> str:
    """List all upcoming events."""
    events = _load_events()
    if not events:
        return "📭 Nenhum evento no calendário."
    # sort by date
    events.sort(key=lambda e: (e["date"], e["time"]))
    formatted = "\n".join(
        [f"📌 {e['title']} → {e['date']} {e['time']}" for e in events]
    )
    return f"📅 Eventos:\n{formatted}"


def remove_event(title: str) -> str:
    """Remove event by title."""
    events = _load_events()
    new_events = [e for e in events if e["title"] != title]
    if len(new_events) == len(events):
        return f"⚠️ Nenhum evento encontrado com título: {title}"
    _save_events(new_events)
    return f"🗑️ Evento removido: {title}"


def register(plugin_manager):
    """Register plugin commands."""
    plugin_manager.register_command("calendar:add", add_event)
    plugin_manager.register_command("calendar:list", list_events)
    plugin_manager.register_command("calendar:remove", remove_event)
