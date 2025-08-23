#!/usr/bin/env python3
"""
💎 GEM OS - Productivity Tools
Task management, time tracking, and productivity features
"""

import logging
import json
import time
import os
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

# =============================================================================
# Enumerations
# =============================================================================

class TaskStatus(Enum):
    """Task status enumeration"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class Priority(Enum):
    """Priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

# =============================================================================
# Dataclasses
# =============================================================================

@dataclass
class Task:
    """Task data structure"""
    id: str
    title: str
    description: str
    priority: Priority
    status: TaskStatus
    created_date: datetime
    due_date: Optional[datetime] = None
    completed_date: Optional[datetime] = None
    tags: List[str] = None
    estimated_minutes: int = 0
    actual_minutes: int = 0
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []

@dataclass
class TimeSession:
    """Time tracking session"""
    id: str
    task_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_minutes: int = 0
    notes: str = ""

@dataclass
class ProductivityGoal:
    """Productivity goal tracking"""
    # NOTE: Non-default arguments (no =) must come before default arguments (=).
    id: str
    title: str
    target_value: str
    target_date: datetime
    is_completed: bool = False
    
# =============================================================================
# Main Class
# =============================================================================

class ProductivityTools:
    """Productivity and task management assistant"""
    
    def __init__(self, data_dir: str = "data"):
        self.logger = logging.getLogger(__name__)
        self.data_dir = data_dir
        self.tasks_file = os.path.join(data_dir, "tasks.json")
        self.sessions_file = os.path.join(data_dir, "time_sessions.json")
        self.goals_file = os.path.join(data_dir, "productivity_goals.json")
        
        # Data storage
        self.tasks: List[Task] = []
        self.time_sessions: List[TimeSession] = []
        self.productivity_goals: List[ProductivityGoal] = []
        
        # Ensure data directory exists
        os.makedirs(self.data_dir, exist_ok=True)
        self.load_data()

    def load_data(self) -> None:
        """Load all productivity data from files"""
        self._load_tasks()
        self._load_time_sessions()
        self._load_goals()
        self.logger.info("Productivity data loaded successfully.")

    def _load_tasks(self) -> None:
        """Load tasks from file"""
        if not os.path.exists(self.tasks_file):
            return
        try:
            with open(self.tasks_file, "r") as f:
                data = json.load(f)
            self.tasks = [
                Task(
                    id=t['id'],
                    title=t['title'],
                    description=t['description'],
                    priority=Priority(t['priority']),
                    status=TaskStatus(t['status']),
                    created_date=datetime.fromisoformat(t['created_date']),
                    due_date=datetime.fromisoformat(t['due_date']) if t['due_date'] else None,
                    completed_date=datetime.fromisoformat(t['completed_date']) if t['completed_date'] else None,
                    tags=t.get('tags', []),
                    estimated_minutes=t.get('estimated_minutes', 0),
                    actual_minutes=t.get('actual_minutes', 0),
                )
                for t in data
            ]
        except Exception as e:
            self.logger.error(f"Error loading tasks: {e}")
            self.tasks = []

    def _load_time_sessions(self) -> None:
        """Load time sessions from file"""
        if not os.path.exists(self.sessions_file):
            return
        try:
            with open(self.sessions_file, "r") as f:
                data = json.load(f)
            self.time_sessions = [
                TimeSession(
                    id=s['id'],
                    task_id=s['task_id'],
                    start_time=datetime.fromisoformat(s['start_time']),
                    end_time=datetime.fromisoformat(s['end_time']) if s['end_time'] else None,
                    duration_minutes=s['duration_minutes'],
                    notes=s['notes'],
                )
                for s in data
            ]
        except Exception as e:
            self.logger.error(f"Error loading time sessions: {e}")
            self.time_sessions = []
            
    def _load_goals(self) -> None:
        """Load productivity goals from file"""
        if not os.path.exists(self.goals_file):
            return
        try:
            with open(self.goals_file, "r") as f:
                data = json.load(f)
            self.productivity_goals = [
                ProductivityGoal(
                    id=g['id'],
                    title=g['title'],
                    target_value=g['target_value'],
                    target_date=datetime.fromisoformat(g['target_date']),
                    is_completed=g['is_completed'],
                )
                for g in data
            ]
        except Exception as e:
            self.logger.error(f"Error loading goals: {e}")
            self.productivity_goals = []

    def save_data(self) -> None:
        """Save all productivity data to files"""
        self._save_tasks()
        self._save_goals()
        self._save_time_sessions()
        
    def _save_tasks(self) -> None:
        """Save tasks to file"""
        try:
            data = [
                {
                    **asdict(t),
                    'priority': t.priority.value,
                    'status': t.status.value,
                    'created_date': t.created_date.isoformat(),
                    'due_date': t.due_date.isoformat() if t.due_date else None,
                    'completed_date': t.completed_date.isoformat() if t.completed_date else None,
                }
                for t in self.tasks
            ]
            with open(self.tasks_file, 'w') as f:
                json.dump(data, f, indent=2)
            self.logger.info("Tasks saved successfully.")
        except Exception as e:
            self.logger.error(f"Error saving tasks: {e}")

    def _save_time_sessions(self) -> None:
        """Save time sessions to file"""
        try:
            data = [
                {
                    **asdict(s),
                    'start_time': s.start_time.isoformat(),
                    'end_time': s.end_time.isoformat() if s.end_time else None,
                }
                for s in self.time_sessions
            ]
            with open(self.sessions_file, 'w') as f:
                json.dump(data, f, indent=2)
            self.logger.info("Time sessions saved successfully.")
        except Exception as e:
            self.logger.error(f"Error saving time sessions: {e}")

    def _save_goals(self) -> None:
        """Save productivity goals to file"""
        try:
            data = [
                {
                    **asdict(g),
                    'target_date': g.target_date.isoformat(),
                }
                for g in self.productivity_goals
            ]
            with open(self.goals_file, 'w') as f:
                json.dump(data, f, indent=2)
            self.logger.info("Productivity goals saved successfully.")
        except Exception as e:
            self.logger.error(f"Error saving productivity goals: {e}")

    def add_task(self, title: str, description: str, priority: str) -> str:
        """Add a new task to the list"""
        try:
            new_task = Task(
                id=str(uuid.uuid4()),
                title=title,
                description=description,
                priority=Priority[priority.upper()],
                status=TaskStatus.PENDING,
                created_date=datetime.now(),
            )
            self.tasks.append(new_task)
            self._save_tasks()
            return f"✅ Task '{title}' added with {priority} priority."
        except KeyError:
            return f"❌ Invalid priority '{priority}'. Please use one of: low, medium, high, urgent."
        except Exception as e:
            return f"❌ Error adding task: {e}"

    def list_tasks(self) -> str:
        """List all tasks"""
        if not self.tasks:
            return "📭 No tasks found."
        
        task_list = [f" - {t.title} ({t.status.value}) - Priority: {t.priority.value}" for t in self.tasks]
        return "📋 Your Tasks:\n" + "\n".join(task_list)

    def add_productivity_goal(self, title: str, target_value: str, target_date_str: str) -> str:
        """Add a new productivity goal"""
        try:
            target_date = datetime.fromisoformat(target_date_str)
            new_goal = ProductivityGoal(
                id=str(uuid.uuid4()),
                title=title,
                target_value=target_value,
                target_date=target_date,
            )
            self.productivity_goals.append(new_goal)
            self._save_goals()
            return f"✅ Productivity goal '{title}' added with a target of {target_date.strftime('%Y-%m-%d')}."
        except ValueError:
            return "❌ Invalid date format. Please use YYYY-MM-DD."
        except Exception as e:
            return f"❌ Error adding goal: {e}"

    def get_productivity_tip(self) -> str:
        """Get a random productivity tip"""
        tips = [
            "Use the Pomodoro Technique: work in focused 25-minute intervals with short breaks.",
            "Prioritize your tasks using the Eisenhower Matrix: Urgent/Important, Urgent/Not Important, etc.",
            "Break down large projects into smaller, manageable tasks to avoid feeling overwhelmed.",
            "Schedule your most challenging work for when you have the most energy.",
            "Avoid multitasking. Focus on one task at a time for better quality and speed."
        ]
        import random
        return f"💡 Productivity Tip: {random.choice(tips)}"
        
    async def check_notifications(self) -> List[str]:
        """Check for overdue tasks or goals to notify the user"""
        notifications: List[str] = []
        now = datetime.now()

        # Check for overdue tasks
        for task in self.tasks:
            if task.due_date and task.status == TaskStatus.PENDING and task.due_date < now:
                notifications.append(f"Task '{task.title}' is overdue!")

        # Check for upcoming goals
        for goal in self.productivity_goals:
            if not goal.is_completed and goal.target_date > now and (goal.target_date - now).days < 7:
                notifications.append(f"Goal '{goal.title}' is coming up on {goal.target_date.strftime('%Y-%m-%d')}.")

        return notifications

    def shutdown(self) -> None:
        """Graceful shutdown"""
        self.save_data()

# =============================================================================
# CLI Test
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("Running ProductivityTools module test...")
    tools = ProductivityTools()
    
    # Add a new task
    print(tools.add_task("Write Report", "Finish the Q3 financial report", "high"))
    
    # Add a new goal
    target_date = datetime.now() + timedelta(days=30)
    print(tools.add_productivity_goal("Read 5 books", "5 books", target_date.isoformat()))

    # List tasks
    print("\n" + tools.list_tasks())
    
    # Get a productivity tip
    print("\n" + tools.get_productivity_tip())
