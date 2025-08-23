#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
💎 GEM OS - Storage Manager (core/storage.py)
Manages data persistence for GEM OS using SQLite.

Responsibilities
----------------
- Initialize and manage a single SQLite database connection.
- Store and retrieve user profiles and key-value settings.
- Store and retrieve conversation history.
- Manage learning data, including sessions, progress, and quizzes.
- Provide a robust, asynchronous interface for all database operations.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union


class Storage:
    """
    Manages all data persistence for GEM OS using a single SQLite database.
    Provides methods for user profiles, settings, history, and learning data.
    """

    def __init__(self, config: Any, logger: Optional[logging.Logger] = None):
        """
        Initializes the Storage manager.

        Args:
            config: The storage configuration object (e.g., a dataclass).
            logger: Optional logger instance.
        """
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        self.db_path = Path(getattr(config, "database_path", "data/user_data.db"))
        self.conn: Optional[sqlite3.Connection] = None

        # Ensure the directory for the database exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.logger.info(f"Storage initialized. Database path: {self.db_path}")

    async def initialize(self) -> None:
        """
        Initializes the database connection and creates all necessary tables.
        This method should be called once at startup.
        """

        def _connect_and_create_tables():
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row  # Allows accessing columns by name
            cursor = self.conn.cursor()

            # Table for general key-value settings
            cursor.execute("""
                           CREATE TABLE IF NOT EXISTS settings
                           (
                               key
                               TEXT
                               PRIMARY
                               KEY,
                               value
                               TEXT
                           )
                           """)

            # Table for conversation history
            cursor.execute("""
                           CREATE TABLE IF NOT EXISTS conversation_history
                           (
                               id
                               INTEGER
                               PRIMARY
                               KEY
                               AUTOINCREMENT,
                               timestamp
                               TEXT
                               DEFAULT
                               CURRENT_TIMESTAMP,
                               role
                               TEXT
                               NOT
                               NULL,
                               content
                               TEXT
                               NOT
                               NULL
                           )
                           """)

            # Table for learning sessions
            cursor.execute('''
                           CREATE TABLE IF NOT EXISTS learning_sessions
                           (
                               id
                               INTEGER
                               PRIMARY
                               KEY
                               AUTOINCREMENT,
                               topic
                               TEXT
                               NOT
                               NULL,
                               session_type
                               TEXT,
                               duration_minutes
                               INTEGER,
                               score
                               REAL,
                               completed
                               BOOLEAN
                               DEFAULT
                               0,
                               timestamp
                               TEXT,
                               notes
                               TEXT,
                               created_at
                               TIMESTAMP
                               DEFAULT
                               CURRENT_TIMESTAMP
                           )
                           ''')

            # Table for quiz questions
            cursor.execute('''
                           CREATE TABLE IF NOT EXISTS quiz_questions
                           (
                               id
                               INTEGER
                               PRIMARY
                               KEY
                               AUTOINCREMENT,
                               topic
                               TEXT
                               NOT
                               NULL,
                               question
                               TEXT
                               NOT
                               NULL,
                               options
                               TEXT,
                               correct_answer
                               TEXT,
                               difficulty
                               TEXT
                               DEFAULT
                               'medium',
                               explanation
                               TEXT,
                               created_at
                               TIMESTAMP
                               DEFAULT
                               CURRENT_TIMESTAMP
                           )
                           ''')

            # Table for learning progress
            cursor.execute('''
                           CREATE TABLE IF NOT EXISTS learning_progress
                           (
                               topic
                               TEXT
                               PRIMARY
                               KEY,
                               level
                               INTEGER
                               DEFAULT
                               1,
                               experience_points
                               INTEGER
                               DEFAULT
                               0,
                               sessions_completed
                               INTEGER
                               DEFAULT
                               0,
                               average_score
                               REAL
                               DEFAULT
                               0.0,
                               last_session
                               TEXT,
                               strengths
                               TEXT,
                               areas_for_improvement
                               TEXT,
                               updated_at
                               TIMESTAMP
                               DEFAULT
                               CURRENT_TIMESTAMP
                           )
                           ''')

            self.conn.commit()
            self.logger.info("Database connection established and all tables ensured.")

        try:
            await asyncio.to_thread(_connect_and_create_tables)
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize database: {e}", exc_info=True)
            raise  # Re-raise to signal critical initialization failure

    async def _execute(self, query: str, params: Union[Dict, Tuple] = ()) -> Optional[sqlite3.Cursor]:
        """A generic asynchronous method to execute SQL queries."""
        if not self.conn:
            self.logger.error("Database not initialized. Cannot execute query.")
            return None

        def _sync_execute():
            try:
                cursor = self.conn.cursor()
                cursor.execute(query, params)
                self.conn.commit()
                return cursor
            except sqlite3.Error as e:
                self.logger.error(f"❌ Database error on query '{query[:50]}...': {e}", exc_info=True)
                return None

        return await asyncio.to_thread(_sync_execute)

    # --- Settings Management ---
    async def set_setting(self, key: str, value: Any) -> bool:
        """Stores a key-value pair. Values are serialized to JSON."""
        try:
            serialized_value = json.dumps(value)
            cursor = await self._execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                (key, serialized_value)
            )
            return cursor is not None
        except TypeError as e:
            self.logger.error(f"❌ Failed to serialize setting '{key}': {e}")
            return False

    async def get_setting(self, key: str, default: Any = None) -> Any:
        """Retrieves a setting by its key. Values are deserialized from JSON."""
        cursor = await self._execute("SELECT value FROM settings WHERE key = ?", (key,))
        if cursor:
            row = cursor.fetchone()
            if row:
                try:
                    return json.loads(row['value'])
                except json.JSONDecodeError:
                    self.logger.error(f"Failed to decode JSON for setting '{key}'")
                    return default
        return default

    # --- Conversation History ---
    async def add_message_to_history(self, role: str, content: str) -> bool:
        """Adds a message to the conversation history."""
        cursor = await self._execute(
            "INSERT INTO conversation_history (role, content) VALUES (?, ?)",
            (role, content)
        )
        return cursor is not None

    async def get_conversation_history(self, limit: int = 100) -> List[Dict[str, str]]:
        """Retrieves a portion of the conversation history."""
        cursor = await self._execute(
            "SELECT role, content FROM conversation_history ORDER BY id DESC LIMIT ?",
            (limit,)
        )
        if cursor:
            rows = cursor.fetchall()
            return [{"role": row['role'], "content": row['content']} for row in reversed(rows)]
        return []

    # --- Learning Data Management ---
    async def save_learning_session(self, session_data: Dict[str, Any]) -> Optional[int]:
        """Saves a learning session and returns its ID."""
        query = """
                INSERT INTO learning_sessions
                (topic, session_type, duration_minutes, score, completed, timestamp, notes)
                VALUES (:topic, :session_type, :duration_minutes, :score, :completed, :timestamp, :notes) \
                """
        cursor = await self._execute(query, session_data)
        return cursor.lastrowid if cursor else None

    async def save_quiz_question(self, question_data: Dict[str, Any]) -> Optional[int]:
        """Saves a quiz question and returns its ID."""
        query = """
                INSERT INTO quiz_questions
                    (topic, question, options, correct_answer, difficulty, explanation)
                VALUES (:topic, :question, :options, :correct_answer, :difficulty, :explanation) \
                """
        # Serialize list to JSON string
        question_data['options'] = json.dumps(question_data.get('options', []))
        cursor = await self._execute(query, question_data)
        return cursor.lastrowid if cursor else None

    async def get_quiz_questions(self, topic: str, difficulty: Optional[str] = None, limit: int = 10) -> List[
        Dict[str, Any]]:
        """Retrieves quiz questions for a given topic."""
        if difficulty:
            query = "SELECT * FROM quiz_questions WHERE topic = ? AND difficulty = ? ORDER BY RANDOM() LIMIT ?"
            params = (topic, difficulty, limit)
        else:
            query = "SELECT * FROM quiz_questions WHERE topic = ? ORDER BY RANDOM() LIMIT ?"
            params = (topic, limit)

        cursor = await self._execute(query, params)
        if not cursor:
            return []

        questions = []
        for row in cursor.fetchall():
            question_dict = dict(row)
            # Deserialize options from JSON string
            question_dict['options'] = json.loads(question_dict.get('options', '[]'))
            questions.append(question_dict)
        return questions

    async def save_learning_progress(self, progress_data: Dict[str, Any]) -> bool:
        """Saves or updates learning progress for a topic."""
        query = """
            INSERT OR REPLACE INTO learning_progress 
            (topic, level, experience_points, sessions_completed, average_score, 
             last_session, strengths, areas_for_improvement, updated_at)
            VALUES (:topic, :level, :experience_points, :sessions_completed, :average_score, 
                    :last_session, :strengths, :areas_for_improvement, CURRENT_TIMESTAMP)
        """
        # Serialize lists to JSON strings
        progress_data['strengths'] = json.dumps(progress_data.get('strengths', []))
        progress_data['areas_for_improvement'] = json.dumps(progress_data.get('areas_for_improvement', []))

        cursor = await self._execute(query, progress_data)
        return cursor is not None

    async def get_learning_progress(self, topic: str) -> Optional[Dict[str, Any]]:
        """Retrieves learning progress for a specific topic."""
        cursor = await self._execute("SELECT * FROM learning_progress WHERE topic = ?", (topic,))
        if cursor:
            row = cursor.fetchone()
            if row:
                progress_dict = dict(row)
                # Deserialize lists from JSON strings
                progress_dict['strengths'] = json.loads(progress_dict.get('strengths', '[]'))
                progress_dict['areas_for_improvement'] = json.loads(progress_dict.get('areas_for_improvement', '[]'))
                return progress_dict
        return None

    def shutdown(self) -> None:
        """Closes the database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
            self.logger.info("Database connection closed.")
