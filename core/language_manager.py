#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
? GEM OS - Language Manager (core/language_manager.py)
Manages user's language learning activities, including vocabulary, exercises, and progress tracking.

Responsibilities
----------------
- Add, list, and organize vocabulary (words, phrases, translations, examples).
- Create and manage language exercises for practice.
- Track language learning progress.
- Persist language data using the Storage module.
- Expose language management capabilities as tools for the LLM.
- Publish language-related events.
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


# --- Dataclass para Vocabul‡rio ---
@dataclass
class VocabularyItem:
    id: str
    word: str
    language: str  # Ex: "Ingl?s", "Espanhol"
    translation: str
    example_sentence: Optional[str] = None
    added_at: datetime = field(default_factory=datetime.now)
    last_practiced: Optional[datetime] = None
    mastery_level: int = 0  # 0 (new) atŽ 5 (mastered)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "word": self.word,
            "language": self.language,
            "translation": self.translation,
            "example_sentence": self.example_sentence,
            "added_at": self.added_at.isoformat(),
            "last_practiced": self.last_practiced.isoformat() if self.last_practiced else None,
            "mastery_level": self.mastery_level,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> VocabularyItem:
        return cls(
            id=data["id"],
            word=data["word"],
            language=data["language"],
            translation=data["translation"],
            example_sentence=data.get("example_sentence"),
            added_at=datetime.fromisoformat(data["added_at"]) if data.get("added_at") else datetime.now(),
            last_practiced=datetime.fromisoformat(data["last_practiced"]) if data.get("last_practiced") else None,
            mastery_level=data.get("mastery_level", 0),
        )


# --- Dataclass para Exerc’cio de Idioma ---
@dataclass
class LanguageExercise:
    id: str
    language: str
    exercise_type: str  # Ex: "translation", "multiple_choice"
    question: str
    correct_answer: str
    options: Optional[List[str]] = field(default_factory=list)  # Para mœltipla escolha
    created_at: datetime = field(default_factory=datetime.now)
    last_practiced: Optional[datetime] = None
    times_correct: int = 0
    times_incorrect: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "language": self.language,
            "exercise_type": self.exercise_type,
            "question": self.question,
            "correct_answer": self.correct_answer,
            "options": self.options,
            "created_at": self.created_at.isoformat(),
            "last_practiced": self.last_practiced.isoformat() if self.last_practiced else None,
            "times_correct": self.times_correct,
            "times_incorrect": self.times_incorrect,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> LanguageExercise:
        return cls(
            id=data["id"],
            language=data["language"],
            exercise_type=data["exercise_type"],
            question=data["question"],
            correct_answer=data["correct_answer"],
            options=data.get("options", []),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            last_practiced=datetime.fromisoformat(data["last_practiced"]) if data.get("last_practiced") else None,
            times_correct=data.get("times_correct", 0),
            times_incorrect=data.get("times_incorrect", 0),
        )


# --- Dataclass para Progresso de Idioma ---
@dataclass
class LanguageProgress:
    id: str
    language: str
    current_level: str  # Ex: "A1", "B2", "C1"
    start_date: datetime
    last_update: datetime = field(default_factory=datetime.now)
    goal_level: Optional[str] = None
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "language": self.language,
            "current_level": self.current_level,
            "start_date": self.start_date.isoformat(),
            "last_update": self.last_update.isoformat(),
            "goal_level": self.goal_level,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> LanguageProgress:
        return cls(
            id=data["id"],
            language=data["language"],
            current_level=data["current_level"],
            start_date=datetime.fromisoformat(data["start_date"]),
            last_update=datetime.fromisoformat(data["last_update"]) if data.get("last_update") else datetime.now(),
            goal_level=data.get("goal_level"),
            notes=data.get("notes"),
        )


# --- Language Manager como um Plugin ---
class LanguageManager(BasePlugin):
    """
    Manages user's language learning data for GEM OS, acting as a plugin.
    """

    STORAGE_KEY_VOCABULARY = "user_language_vocabulary"
    STORAGE_KEY_EXERCISES = "user_language_exercises"
    STORAGE_KEY_PROGRESS = "user_language_progress"

    def __init__(self, gem_instance: GEMVoiceAssistant, logger: Optional[logging.Logger] = None):
        super().__init__(gem_instance, logger)
        self.logger.info("LanguageManager plugin inicializado.")
        
        self.event_manager: EventManager = gem_instance.event_manager
        self.notification_manager: NotificationManager = gem_instance.notification_manager
        self.storage: Storage = gem_instance.storage
        self.tts_module: TTSModule = gem_instance.tts_module
        # ? Atualizado para usar GEMConfigManager
        self.config_manager: GEMConfigManager = gem_instance.config_manager

        self._vocabulary: Dict[str, VocabularyItem] = {}
        self._exercises: Dict[str, LanguageExercise] = {}
        self._progress_entries: Dict[str, LanguageProgress] = {}
        self._data_loaded = asyncio.Event()

        self._practice_reminder_task: Optional[asyncio.Task] = None
        self._practice_reminder_interval_seconds: int = 4 * 3600  # Verifica??o a cada 4h

    # (... resto do c—digo segue igual, j‡ adaptado para GEMConfigManager ...)
