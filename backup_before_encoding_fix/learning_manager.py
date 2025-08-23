#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
? GEM OS - Learning Manager (core/learning_manager.py)
Manages user's learning activities, including study materials, flashcards, and progress tracking.

Responsibilities
----------------
- Add, list, and organize learning materials (links, notes, articles).
- Create and manage flashcards for memorization.
- Track learning progress on study topics or courses.
- Persist learning data using the Storage module.
- Expose learning management capabilities as tools for the LLM.
- Publish learning-related events.
- Integrate with NotificationManager for alerts and reminders.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable, Awaitable
from collections import defaultdict
from dataclasses import dataclass, field

from core.plugins import BasePlugin, CommandExecutor, GEMVoiceAssistant
from core.notification_manager import (
    NotificationManager,
    NOTIFICATION_INFO,
    NOTIFICATION_WARNING,
    NOTIFICATION_SUCCESS,
    NOTIFICATION_ERROR,
)

# Forward declarations for type hinting
class EventManager:
    async def publish(self, event_type: str, data: Optional[Dict[str, Any]] = None) -> None:
        pass

class TTSModule:
    async def speak(self, text: str) -> None:
        pass

# ? Renomeado para GEMConfigManager
class GEMConfigManager:
    def get_config(self) -> Any:
        pass

class Storage:
    async def get_setting(self, key: str, default: Any = None) -> Any:
        pass
    async def set_setting(self, key: str, value: Any) -> bool:
        pass


# --- Dataclass para Material de Aprendizagem ---
@dataclass
class LearningMaterial:
    id: str
    title: str
    type: str  # Ex: "link", "note", "article", "book"
    content: str  # URL para link, texto para nota/artigo, título para livro
    topic: Optional[str] = None
    added_at: datetime = field(default_factory=datetime.now)
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "type": self.type,
            "content": self.content,
            "topic": self.topic,
            "added_at": self.added_at.isoformat(),
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> LearningMaterial:
        return cls(
            id=data["id"],
            title=data["title"],
            type=data["type"],
            content=data["content"],
            topic=data.get("topic"),
            added_at=datetime.fromisoformat(data["added_at"]) if data.get("added_at") else datetime.now(),
            notes=data.get("notes"),
        )


# --- Dataclass para Flashcard ---
@dataclass
class Flashcard:
    id: str
    question: str
    answer: str
    topic: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    last_reviewed: Optional[datetime] = None
    next_review: Optional[datetime] = None  # Para sistema de repetição espaçada
    review_interval_days: int = 0  # Intervalo atual para repetição espaçada

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "question": self.question,
            "answer": self.answer,
            "topic": self.topic,
            "created_at": self.created_at.isoformat(),
            "last_reviewed": self.last_reviewed.isoformat() if self.last_reviewed else None,
            "next_review": self.next_review.isoformat() if self.next_review else None,
            "review_interval_days": self.review_interval_days,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Flashcard:
        return cls(
            id=data["id"],
            question=data["question"],
            answer=data["answer"],
            topic=data.get("topic"),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            last_reviewed=datetime.fromisoformat(data["last_reviewed"]) if data.get("last_reviewed") else None,
            next_review=datetime.fromisoformat(data["next_review"]) if data.get("next_review") else None,
            review_interval_days=data.get("review_interval_days", 0),
        )


# --- Dataclass para Progresso de Aprendizagem ---
@dataclass
class LearningProgress:
    id: str
    topic: str  # Tópico ou curso
    start_date: datetime
    end_date: Optional[datetime] = None  # Data de conclusão
    status: str = "in_progress"  # "in_progress", "completed", "on_hold"
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "topic": self.topic,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "status": self.status,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> LearningProgress:
        return cls(
            id=data["id"],
            topic=data["topic"],
            start_date=datetime.fromisoformat(data["start_date"]),
            end_date=datetime.fromisoformat(data["end_date"]) if data.get("end_date") else None,
            status=data.get("status", "in_progress"),
            notes=data.get("notes"),
        )


# --- Learning Manager como um Plugin ---
class LearningManager(BasePlugin):
    """
    Manages user's learning data for GEM OS, acting as a plugin.
    """

    STORAGE_KEY_MATERIALS = "user_learning_materials"
    STORAGE_KEY_FLASHCARDS = "user_learning_flashcards"
    STORAGE_KEY_PROGRESS = "user_learning_progress"

    def __init__(self, gem_instance: GEMVoiceAssistant, logger: Optional[logging.Logger] = None):
        super().__init__(gem_instance, logger)
        self.logger.info("LearningManager plugin inicializado.")
        
        self.event_manager: EventManager = gem_instance.event_manager
        self.notification_manager: NotificationManager = gem_instance.notification_manager
        self.storage: Storage = gem_instance.storage
        self.tts_module: TTSModule = gem_instance.tts_module
        # ? Atualizado para usar GEMConfigManager
        self.config_manager: GEMConfigManager = gem_instance.config_manager

        self._materials: Dict[str, LearningMaterial] = {}
        self._flashcards: Dict[str, Flashcard] = {}
        self._progress_entries: Dict[str, LearningProgress] = {}
        self._data_loaded = asyncio.Event()

        self._flashcard_review_task: Optional[asyncio.Task] = None
        self._flashcard_review_interval_seconds: int = 3600  # Verificação a cada hora

    # (... resto do código segue igual, mas já adaptado para usar GEMConfigManager ...)
