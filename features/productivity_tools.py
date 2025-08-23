#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
💎 GEM OS - Productivity Tools
Task management and productivity features for enhanced daily life
"""

import asyncio
import json
import logging
import schedule
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
import sqlite3


@dataclass
class Task:
    """Task data structure."""
    id: Optional[int] = None
    title: str = ""
    description: str = ""
    priority: str = "medium"  # low, medium, high, urgent
    status: str = "pending"  # pending, in_progress, completed, cancelled
    due_date: Optional[str] = None
    created_at: str = ""
    completed_at: Optional[str] = None
    category: str = "general"
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


@dataclass
class Reminder:
    """Reminder data structure."""
    id: Optional[int] = None
    title: str = ""
    description: str = ""
    reminder_time: str = ""
    repeat_pattern: Optional[str] = None  # daily, weekly, monthly
    is_active: bool = True
    created_at: str = ""
    last_triggered: Optional[str] = None
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


@dataclass
class Note:
    """Note data structure."""
    id: Optional[int] = None
    title: str = ""
    content: str = ""
    category: str = "general"
    tags: List[str] = None
    created_at: str = ""
    updated_at: str = ""
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = self.created_at


@dataclass
class TimeEntry:
    """Time tracking entry."""
    id: Optional[int] = None
    task_id: Optional[int] = None
    activity: str = ""
    start_time: str = ""
    end_time: Optional[str] = None
    duration_minutes: int = 0
    description: str = ""
    
    def __post_init__(self):
        if not self.start_time:
            self.start_time = datetime.now().isoformat()


class ProductivityDatabase:
    """Productivity data storage and management."""
    
    def __init__(self, db_path: Path, logger: logging.Logger):
        self.db_path = db_path
        self.logger = logger
        self._init_database()
    
    def _init_database(self):
        """Initialize productivity database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Tasks table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS tasks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        description TEXT,
                        priority TEXT DEFAULT 'medium',
                        status TEXT DEFAULT 'pending',
                        due_date TEXT,
                        created_at TEXT,
                        completed_at TEXT,
                        category TEXT DEFAULT 'general',
                        tags TEXT  -- JSON array
                    )
                ''')
                
                # Reminders table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS reminders (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        description TEXT,
                        reminder_time TEXT,
                        repeat_pattern TEXT,
                        is_active BOOLEAN DEFAULT 1,
                        created_at TEXT,
                        last_triggered TEXT
                    )
                ''')
                
                # Notes table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS notes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        content TEXT,
                        category TEXT DEFAULT 'general',
                        tags TEXT,  -- JSON array
                        created_at TEXT,
                        updated_at TEXT
                    )
                ''')
                
                # Time tracking table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS time_entries (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        task_id INTEGER,
                        activity TEXT,
                        start_time TEXT,
                        end_time TEXT,
                        duration_minutes INTEGER DEFAULT 0,
                        description TEXT,
                        FOREIGN KEY (task_id) REFERENCES tasks (id)
                    )
                ''')
                
                conn.commit()
                self.logger.info("Productivity database initialized")
        
        except Exception as e:
            self.logger.error(f"Productivity database initialization error: {e}")
    
    def add_task(self, task: Task) -> int:
        """Add new task."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO tasks 
                    (title, description, priority, status, due_date, created_at, category, tags)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    task.title, task.description, task.priority, task.status,
                    task.due_date, task.created_at, task.category, json.dumps(task.tags)
                ))
                conn.commit()
                return cursor.lastrowid
        
        except Exception as e:
            self.logger.error(f"Error adding task: {e}")
            return 0
    
    def get_tasks(self, status: Optional[str] = None, category: Optional[str] = None) -> List[Task]:
        """Get tasks with optional filtering."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                query = "SELECT id, title, description, priority, status, due_date, created_at, completed_at, category, tags FROM tasks"
                params = []
                conditions = []
                
                if status:
                    conditions.append("status = ?")
                    params.append(status)
                
                if category:
                    conditions.append("category = ?")
                    params.append(category)
                
                if conditions:
                    query += " WHERE " + " AND ".join(conditions)
                
                query += " ORDER BY created_at DESC"
                
                cursor.execute(query, params)
                
                tasks = []
                for row in cursor.fetchall():
                    task = Task(
                        id=row[0], title=row[1], description=row[2], priority=row[3],
                        status=row[4], due_date=row[5], created_at=row[6],
                        completed_at=row[7], category=row[8],
                        tags=json.loads(row[9]) if row[9] else []
                    )
                    tasks.append(task)
                
                return tasks
        
        except Exception as e:
            self.logger.error(f"Error getting tasks: {e}")
            return []
    
    def update_task_status(self, task_id: int, status: str) -> bool:
        """Update task status."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                completed_at = datetime.now().isoformat() if status == "completed" else None
                
                cursor.execute('''
                    UPDATE tasks SET status = ?, completed_at = ? WHERE id = ?
                ''', (status, completed_at, task_id))
                
                conn.commit()
                return cursor.rowcount > 0
        
        except Exception as e:
            self.logger.error(f"Error updating task status: {e}")
            return False
    
    def add_reminder(self, reminder: Reminder) -> int:
        """Add new reminder."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO reminders 
                    (title, description, reminder_time, repeat_pattern, is_active, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    reminder.title, reminder.description, reminder.reminder_time,
                    reminder.repeat_pattern, reminder.is_active, reminder.created_at
                ))
                conn.commit()
                return cursor.lastrowid
        
        except Exception as e:
            self.logger.error(f"Error adding reminder: {e}")
            return 0
    
    def get_active_reminders(self) -> List[Reminder]:
        """Get active reminders."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, title, description, reminder_time, repeat_pattern, 
                           is_active, created_at, last_triggered
                    FROM reminders WHERE is_active = 1
                ''')
                
                reminders = []
                for row in cursor.fetchall():
                    reminder = Reminder(
                        id=row[0], title=row[1], description=row[2], reminder_time=row[3],
                        repeat_pattern=row[4], is_active=bool(row[5]), created_at=row[6],
                        last_triggered=row[7]
                    )
                    reminders.append(reminder)
                
                return reminders
        
        except Exception as e:
            self.logger.error(f"Error getting reminders: {e}")
            return []
    
    def update_reminder_triggered(self, reminder_id: int):
        """Update reminder last triggered time."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE reminders SET last_triggered = ? WHERE id = ?
                ''', (datetime.now().isoformat(), reminder_id))
                conn.commit()
        
        except Exception as e:
            self.logger.error(f"Error updating reminder: {e}")
    
    def add_note(self, note: Note) -> int:
        """Add new note."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO notes 
                    (title, content, category, tags, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    note.title, note.content, note.category, json.dumps(note.tags),
                    note.created_at, note.updated_at
                ))
                conn.commit()
                return cursor.lastrowid
        
        except Exception as e:
            self.logger.error(f"Error adding note: {e}")
            return 0
    
    def get_notes(self, category: Optional[str] = None, limit: int = 10) -> List[Note]:
        """Get notes with optional filtering."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if category:
                    cursor.execute('''
                        SELECT id, title, content, category, tags, created_at, updated_at
                        FROM notes WHERE category = ? ORDER BY updated_at DESC LIMIT ?
                    ''', (category, limit))
                else:
                    cursor.execute('''
                        SELECT id, title, content, category, tags, created_at, updated_at
                        FROM notes ORDER BY updated_at DESC LIMIT ?
                    ''', (limit,))
                
                notes = []
                for row in cursor.fetchall():
                    note = Note(
                        id=row[0], title=row[1], content=row[2], category=row[3],
                        tags=json.loads(row[4]) if row[4] else [],
                        created_at=row[5], updated_at=row[6]
                    )
                    notes.append(note)
                
                return notes
        
        except Exception as e:
            self.logger.error(f"Error getting notes: {e}")
            return []


class TaskManager:
    """Task management system."""
    
    def __init__(self, database: ProductivityDatabase, logger: logging.Logger):
        self.database = database
        self.logger = logger
    
    async def create_task(self, title: str, description: str = "", priority: str = "medium", 
                         due_date: Optional[str] = None, category: str = "general") -> str:
        """Create a new task."""
        try:
            task = Task(
                title=title,
                description=description,
                priority=priority,
                due_date=due_date,
                category=category
            )
            
            task_id = self.database.add_task(task)
            
            if task_id:
                return f"Tarefa criada: '{title}' (ID: {task_id})"
            else:
                return "Erro ao criar tarefa"
        
        except Exception as e:
            self.logger.error(f"Error creating task: {e}")
            return "Erro ao criar tarefa"
    
    async def list_tasks(self, status: str = "pending") -> str:
        """List tasks by status."""
        try:
            tasks = self.database.get_tasks(status=status)
            
            if not tasks:
                return f"Nenhuma tarefa {status} encontrada"
            
            task_list = f"Tarefas {status}:\n\n"
            
            for task in tasks[:10]:  # Limit to 10 tasks
                task_list += f"• {task.title}"
                
                if task.priority in ["high", "urgent"]:
                    task_list += f" (Prioridade: {task.priority})"
                
                if task.due_date:
                    task_list += f" - Prazo: {task.due_date}"
                
                task_list += "\n"
            
            if len(tasks) > 10:
                task_list += f"\n... e mais {len(tasks) - 10} tarefas"
            
            return task_list
        
        except Exception as e:
            self.logger.error(f"Error listing tasks: {e}")
            return "Erro ao listar tarefas"
    
    async def complete_task(self, task_identifier: str) -> str:
        """Mark task as completed."""
        try:
            # Try to find task by ID or title
            if task_identifier.isdigit():
                task_id = int(task_identifier)
                success = self.database.update_task_status(task_id, "completed")
                
                if success:
                    return f"Tarefa {task_id} marcada como concluída"
                else:
                    return f"Tarefa {task_id} não encontrada"
            else:
                # Find by title
                tasks = self.database.get_tasks(status="pending")
                
                for task in tasks:
                    if task_identifier.lower() in task.title.lower():
                        success = self.database.update_task_status(task.id, "completed")
                        
                        if success:
                            return f"Tarefa '{task.title}' marcada como concluída"
                        break
                
                return f"Tarefa '{task_identifier}' não encontrada"
        
        except Exception as e:
            self.logger.error(f"Error completing task: {e}")
            return "Erro ao concluir tarefa"
    
    async def get_task_summary(self) -> str:
        """Get task summary."""
        try:
            pending_tasks = self.database.get_tasks(status="pending")
            completed_tasks = self.database.get_tasks(status="completed")
            
            # Count by priority
            high_priority = len([t for t in pending_tasks if t.priority in ["high", "urgent"]])
            
            # Count overdue tasks
            today = datetime.now().date()
            overdue = 0
            
            for task in pending_tasks:
                if task.due_date:
                    try:
                        due_date = datetime.fromisoformat(task.due_date).date()
                        if due_date < today:
                            overdue += 1
                    except:
                        pass
            
            summary = f"Resumo de tarefas:\n"
            summary += f"• Pendentes: {len(pending_tasks)}\n"
            summary += f"• Concluídas: {len(completed_tasks)}\n"
            summary += f"• Alta prioridade: {high_priority}\n"
            
            if overdue > 0:
                summary += f"• Atrasadas: {overdue}\n"
            
            return summary
        
        except Exception as e:
            self.logger.error(f"Error getting task summary: {e}")
            return "Erro ao obter resumo de tarefas"


class ReminderManager:
    """Reminder management system."""
    
    def __init__(self, database: ProductivityDatabase, logger: logging.Logger):
        self.database = database
        self.logger = logger
        self.reminder_callbacks: List[callable] = []
        
        # Schedule reminder checks
        schedule.every().minute.do(self._check_reminders)
    
    def _check_reminders(self):
        """Check for due reminders."""
        try:
            reminders = self.database.get_active_reminders()
            current_time = datetime.now()
            
            for reminder in reminders:
                try:
                    reminder_time = datetime.fromisoformat(reminder.reminder_time)
                    
                    # Check if reminder is due (within 1 minute)
                    if abs((current_time - reminder_time).total_seconds()) <= 60:
                        # Check if not already triggered recently
                        if not reminder.last_triggered or \
                           (current_time - datetime.fromisoformat(reminder.last_triggered)).total_seconds() > 3600:
                            
                            asyncio.create_task(self._trigger_reminder(reminder))
                            self.database.update_reminder_triggered(reminder.id)
                
                except Exception as e:
                    self.logger.error(f"Error checking reminder {reminder.id}: {e}")
        
        except Exception as e:
            self.logger.error(f"Error in reminder check: {e}")
    
    async def _trigger_reminder(self, reminder: Reminder):
        """Trigger reminder notification."""
        message = f"Lembrete: {reminder.title}"
        if reminder.description:
            message += f" - {reminder.description}"
        
        self.logger.info(f"Reminder triggered: {message}")
        
        # Call registered callbacks
        for callback in self.reminder_callbacks:
            try:
                await callback(reminder, message)
            except Exception as e:
                self.logger.error(f"Reminder callback error: {e}")
    
    def add_reminder_callback(self, callback: callable):
        """Add reminder callback."""
        self.reminder_callbacks.append(callback)
    
    async def create_reminder(self, title: str, reminder_time: str, 
                            description: str = "", repeat_pattern: Optional[str] = None) -> str:
        """Create a new reminder."""
        try:
            # Parse reminder time
            try:
                if ":" in reminder_time:
                    # Time format like "14:30"
                    time_parts = reminder_time.split(":")
                    hour = int(time_parts[0])
                    minute = int(time_parts[1])
                    
                    # Set for today or tomorrow if time has passed
                    reminder_datetime = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
                    
                    if reminder_datetime <= datetime.now():
                        reminder_datetime += timedelta(days=1)
                else:
                    # Relative time like "30 minutes"
                    if "minute" in reminder_time:
                        minutes = int(reminder_time.split()[0])
                        reminder_datetime = datetime.now() + timedelta(minutes=minutes)
                    elif "hour" in reminder_time:
                        hours = int(reminder_time.split()[0])
                        reminder_datetime = datetime.now() + timedelta(hours=hours)
                    else:
                        return "Formato de horário não reconhecido"
            
            except (ValueError, IndexError):
                return "Formato de horário inválido"
            
            reminder = Reminder(
                title=title,
                description=description,
                reminder_time=reminder_datetime.isoformat(),
                repeat_pattern=repeat_pattern
            )
            
            reminder_id = self.database.add_reminder(reminder)
            
            if reminder_id:
                time_str = reminder_datetime.strftime("%H:%M de %d/%m")
                return f"Lembrete criado: '{title}' para {time_str}"
            else:
                return "Erro ao criar lembrete"
        
        except Exception as e:
            self.logger.error(f"Error creating reminder: {e}")
            return "Erro ao criar lembrete"
    
    async def list_reminders(self) -> str:
        """List active reminders."""
        try:
            reminders = self.database.get_active_reminders()
            
            if not reminders:
                return "Nenhum lembrete ativo"
            
            reminder_list = "Lembretes ativos:\n\n"
            
            for reminder in reminders[:10]:  # Limit to 10
                try:
                    reminder_time = datetime.fromisoformat(reminder.reminder_time)
                    time_str = reminder_time.strftime("%H:%M de %d/%m")
                    
                    reminder_list += f"• {reminder.title} - {time_str}"
                    
                    if reminder.repeat_pattern:
                        reminder_list += f" (repete {reminder.repeat_pattern})"
                    
                    reminder_list += "\n"
                
                except Exception:
                    reminder_list += f"• {reminder.title} - horário inválido\n"
            
            return reminder_list
        
        except Exception as e:
            self.logger.error(f"Error listing reminders: {e}")
            return "Erro ao listar lembretes"


class NoteManager:
    """Note management system."""
    
    def __init__(self, database: ProductivityDatabase, logger: logging.Logger):
        self.database = database
        self.logger = logger
    
    async def create_note(self, title: str, content: str, category: str = "general") -> str:
        """Create a new note."""
        try:
            note = Note(
                title=title,
                content=content,
                category=category
            )
            
            note_id = self.database.add_note(note)
            
            if note_id:
                return f"Nota criada: '{title}' (ID: {note_id})"
            else:
                return "Erro ao criar nota"
        
        except Exception as e:
            self.logger.error(f"Error creating note: {e}")
            return "Erro ao criar nota"
    
    async def list_notes(self, category: Optional[str] = None) -> str:
        """List notes."""
        try:
            notes = self.database.get_notes(category=category, limit=10)
            
            if not notes:
                category_text = f" da categoria {category}" if category else ""
                return f"Nenhuma nota{category_text} encontrada"
            
            note_list = "Notas:\n\n"
            
            for note in notes:
                note_list += f"• {note.title}"
                
                if note.category != "general":
                    note_list += f" ({note.category})"
                
                # Show first 50 characters of content
                if note.content:
                    preview = note.content[:50]
                    if len(note.content) > 50:
                        preview += "..."
                    note_list += f"\n  {preview}"
                
                note_list += "\n\n"
            
            return note_list
        
        except Exception as e:
            self.logger.error(f"Error listing notes: {e}")
            return "Erro ao listar notas"


class ProductivityTools:
    """Main productivity tools manager."""
    
    def __init__(self, gem_assistant, logger: Optional[logging.Logger] = None):
        self.gem = gem_assistant
        self.logger = logger or logging.getLogger("ProductivityTools")
        
        # Initialize database
        db_path = Path.home() / ".gem" / "data" / "productivity.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.database = ProductivityDatabase(db_path, self.logger)
        
        # Initialize managers
        self.task_manager = TaskManager(self.database, self.logger)
        self.reminder_manager = ReminderManager(self.database, self.logger)
        self.note_manager = NoteManager(self.database, self.logger)
        
        # Settings
        self.productivity_enabled = True
        self.voice_notifications = True
    
    async def initialize(self):
        """Initialize productivity tools."""
        self.logger.info("Initializing productivity tools...")
        
        # Register reminder callback
        self.reminder_manager.add_reminder_callback(self._handle_reminder)
        
        # Start scheduler
        asyncio.create_task(self._run_scheduler())
        
        self.logger.info("Productivity tools initialized")
    
    async def _run_scheduler(self):
        """Run the reminder scheduler."""
        while True:
            try:
                schedule.run_pending()
                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                self.logger.error(f"Scheduler error: {e}")
                await asyncio.sleep(60)
    
    async def _handle_reminder(self, reminder: Reminder, message: str):
        """Handle reminder notification."""
        if self.productivity_enabled and self.voice_notifications and self.gem.tts_module:
            await self.gem.tts_module.speak(message)
    
    # Task management methods
    async def create_task(self, title: str, description: str = "", priority: str = "medium") -> str:
        """Create a new task."""
        return await self.task_manager.create_task(title, description, priority)
    
    async def list_tasks(self, status: str = "pending") -> str:
        """List tasks."""
        return await self.task_manager.list_tasks(status)
    
    async def complete_task(self, task_identifier: str) -> str:
        """Complete a task."""
        return await self.task_manager.complete_task(task_identifier)
    
    async def get_task_summary(self) -> str:
        """Get task summary."""
        return await self.task_manager.get_task_summary()
    
    # Reminder management methods
    async def create_reminder(self, title: str, reminder_time: str = "30 minutes", 
                            description: str = "") -> str:
        """Create a new reminder."""
        return await self.reminder_manager.create_reminder(title, reminder_time, description)
    
    async def list_reminders(self) -> str:
        """List active reminders."""
        return await self.reminder_manager.list_reminders()
    
    # Note management methods
    async def create_note(self, title: str, content: str, category: str = "general") -> str:
        """Create a new note."""
        return await self.note_manager.create_note(title, content, category)
    
    async def list_notes(self, category: Optional[str] = None) -> str:
        """List notes."""
        return await self.note_manager.list_notes(category)
    
    # Productivity insights
    async def get_productivity_summary(self) -> str:
        """Get overall productivity summary."""
        try:
            summary = "Resumo de produtividade:\n\n"
            
            # Task summary
            task_summary = await self.task_manager.get_task_summary()
            summary += task_summary + "\n"
            
            # Recent activity
            recent_tasks = self.database.get_tasks(status="completed")
            today = datetime.now().date()
            
            completed_today = 0
            for task in recent_tasks:
                if task.completed_at:
                    try:
                        completed_date = datetime.fromisoformat(task.completed_at).date()
                        if completed_date == today:
                            completed_today += 1
                    except:
                        pass
            
            summary += f"• Tarefas concluídas hoje: {completed_today}\n"
            
            # Reminders
            active_reminders = len(self.database.get_active_reminders())
            summary += f"• Lembretes ativos: {active_reminders}\n"
            
            # Notes
            recent_notes = self.database.get_notes(limit=100)
            summary += f"• Total de notas: {len(recent_notes)}\n"
            
            return summary
        
        except Exception as e:
            self.logger.error(f"Error getting productivity summary: {e}")
            return "Erro ao obter resumo de produtividade"
    
    async def suggest_productivity_action(self) -> str:
        """Suggest a productivity action."""
        try:
            # Get pending tasks
            pending_tasks = self.database.get_tasks(status="pending")
            
            if not pending_tasks:
                return "Parabéns! Você não tem tarefas pendentes. Que tal criar uma nova tarefa ou fazer algumas anotações?"
            
            # Find high priority tasks
            high_priority = [t for t in pending_tasks if t.priority in ["high", "urgent"]]
            
            if high_priority:
                task = high_priority[0]
                return f"Você tem uma tarefa de alta prioridade: '{task.title}'. Que tal trabalhar nela agora?"
            
            # Find overdue tasks
            today = datetime.now().date()
            overdue = []
            
            for task in pending_tasks:
                if task.due_date:
                    try:
                        due_date = datetime.fromisoformat(task.due_date).date()
                        if due_date < today:
                            overdue.append(task)
                    except:
                        pass
            
            if overdue:
                task = overdue[0]
                return f"Você tem uma tarefa atrasada: '{task.title}'. É importante concluí-la."
            
            # Suggest oldest task
            if pending_tasks:
                task = pending_tasks[-1]  # Oldest task
                return f"Que tal trabalhar na tarefa '{task.title}'? Ela está pendente há algum tempo."
            
            return "Você está em dia com suas tarefas! Continue assim!"
        
        except Exception as e:
            self.logger.error(f"Error suggesting productivity action: {e}")
            return "Mantenha-se produtivo! Organize suas tarefas e lembretes."
    
    def enable_productivity_tools(self, enabled: bool = True):
        """Enable/disable productivity tools."""
        self.productivity_enabled = enabled
        self.logger.info(f"Productivity tools {'enabled' if enabled else 'disabled'}")
    
    def enable_voice_notifications(self, enabled: bool = True):
        """Enable/disable voice notifications."""
        self.voice_notifications = enabled
        self.logger.info(f"Voice notifications {'enabled' if enabled else 'disabled'}")
    
    async def quick_capture(self, text: str) -> str:
        """Quick capture of ideas/tasks."""
        try:
            # Determine if it's a task or note based on keywords
            task_keywords = ["fazer", "completar", "terminar", "lembrar de", "preciso"]
            
            is_task = any(keyword in text.lower() for keyword in task_keywords)
            
            if is_task:
                return await self.create_task(text)
            else:
                return await self.create_note("Captura rápida", text)
        
        except Exception as e:
            self.logger.error(f"Error in quick capture: {e}")
            return "Erro na captura rápida"