#!/usr/bin/env python3
"""
💎 GEM OS - Health Assistant
Health and wellness tracking and reminders
"""

import logging
import json
import time
import os
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

# =============================================================================
# Dataclasses
# =============================================================================

@dataclass
class HealthReminder:
    """Health reminder data structure"""
    id: str
    title: str
    description: str
    frequency: str  # daily, weekly, monthly, custom
    next_reminder: datetime
    is_active: bool = True
    category: str = "general"  # medication, exercise, checkup, etc.

@dataclass
class HealthMetric:
    """Health metric tracking"""
    date: datetime
    metric_type: str  # weight, blood_pressure, steps, etc.
    value: str
    unit: str
    notes: str = ""

@dataclass
class WellnessGoal:
    """Wellness goal tracking"""
    # NOTE: Non-default arguments (no =) must come before default arguments (=).
    id: str
    title: str
    target_value: str
    category: str
    target_date: datetime
    current_value: str = "0"
    is_completed: bool = False

# =============================================================================
# Main Class
# =============================================================================

class HealthAssistant:
    """Health and wellness assistant"""
    
    def __init__(self, data_dir: str = "data"):
        self.logger = logging.getLogger(__name__)
        self.data_dir = data_dir
        self.health_file = os.path.join(data_dir, "health_data.json")
        
        # Health data storage
        self.reminders: List[HealthReminder] = []
        self.metrics: List[HealthMetric] = []
        self.goals: List[WellnessGoal] = []
        
        # Ensure data directory exists
        os.makedirs(self.data_dir, exist_ok=True)
        self.load_health_data()

    def load_health_data(self) -> None:
        """Load health data from JSON file"""
        if not os.path.exists(self.health_file):
            self.logger.info("Health data file not found. Starting with empty data.")
            return

        try:
            with open(self.health_file, "r") as f:
                data = json.load(f)

            # Rebuild dataclass objects from loaded data
            self.reminders = [
                HealthReminder(**{**r, 'next_reminder': datetime.fromisoformat(r['next_reminder'])})
                for r in data.get("reminders", [])
            ]
            self.metrics = [
                HealthMetric(**{**m, 'date': datetime.fromisoformat(m['date'])})
                for m in data.get("metrics", [])
            ]
            self.goals = [
                WellnessGoal(**{**g, 'target_date': datetime.fromisoformat(g['target_date'])})
                for g in data.get("goals", [])
            ]
            self.logger.info("Health data loaded successfully.")
        except Exception as e:
            self.logger.error(f"Error loading health data, file may be corrupted: {e}")
            self.reminders, self.metrics, self.goals = [], [], []

    def save_health_data(self) -> None:
        """Save health data to JSON file"""
        try:
            data: Dict[str, Any] = {
                "reminders": [asdict(r) for r in self.reminders],
                "metrics": [asdict(m) for m in self.metrics],
                "goals": [asdict(g) for g in self.goals],
            }
            
            # Convert datetime objects to ISO format strings for serialization
            for r in data["reminders"]:
                r['next_reminder'] = r['next_reminder'].isoformat()
            for m in data["metrics"]:
                m['date'] = m['date'].isoformat()
            for g in data["goals"]:
                g['target_date'] = g['target_date'].isoformat()
                
            with open(self.health_file, "w") as f:
                json.dump(data, f, indent=2)
                
            self.logger.info("Health data saved successfully.")
        except Exception as e:
            self.logger.error(f"Error saving health data: {e}")

    def add_health_reminder(self, title: str, description: str, frequency: str, category: str) -> str:
        """Add a new health reminder"""
        reminder_id = str(uuid.uuid4())
        next_reminder = datetime.now() + timedelta(days=1)  # Default for 'daily'
        
        new_reminder = HealthReminder(
            id=reminder_id,
            title=title,
            description=description,
            frequency=frequency,
            next_reminder=next_reminder,
            category=category,
        )
        self.reminders.append(new_reminder)
        self.save_health_data()
        return f"✅ Health reminder '{title}' added."

    def add_health_metric(self, metric_type: str, value: str, unit: str, notes: str = "") -> str:
        """Add a new health metric reading"""
        new_metric = HealthMetric(
            date=datetime.now(),
            metric_type=metric_type,
            value=value,
            unit=unit,
            notes=notes,
        )
        self.metrics.append(new_metric)
        self.save_health_data()
        return f"✅ Health metric '{metric_type}' recorded: {value} {unit}."

    def add_wellness_goal(self, title: str, target_value: str, category: str, target_date: datetime) -> str:
        """Add a new wellness goal"""
        goal_id = str(uuid.uuid4())
        new_goal = WellnessGoal(
            id=goal_id,
            title=title,
            target_value=target_value,
            category=category,
            target_date=target_date,
        )
        self.goals.append(new_goal)
        self.save_health_data()
        return f"✅ Wellness goal '{title}' added with a target date of {target_date.strftime('%Y-%m-%d')}."

    def get_health_tip(self, category: str = "general") -> str:
        """Get a random health tip based on category"""
        tips: Dict[str, List[str]] = {
            "exercise": [
                "Regular exercise boosts your mood and energy.",
                "Aim for at least 30 minutes of moderate activity most days.",
                "Incorporate strength training to build muscle and bone density.",
            ],
            "nutrition": [
                "Stay hydrated by drinking plenty of water throughout the day.",
                "Eat a balanced diet rich in fruits, vegetables, and whole grains.",
                "Mindful eating helps you pay attention to your body's hunger and fullness cues."
            ],
            "mental_health": [
                "Practice mindfulness or meditation to reduce stress.",
                "Get enough sleep to support your mental and physical health.",
                "Connect with friends and family to strengthen your support network."
            ],
            "general": [
                "Listen to your body. It often knows what it needs.",
                "Small, consistent changes lead to long-term health benefits.",
                "Don't be afraid to seek professional advice from a doctor or therapist."
            ]
        }
        import random
        return random.choice(tips.get(category, tips["general"]))

    def get_overdue_reminders(self) -> List[HealthReminder]:
        """Check for overdue reminders"""
        now = datetime.now()
        overdue_reminders: List[HealthReminder] = []
        for reminder in self.reminders:
            if reminder.is_active and reminder.next_reminder < now:
                overdue_reminders.append(reminder)
                # Update next reminder time based on frequency
                if reminder.frequency == "daily":
                    reminder.next_reminder = now + timedelta(days=1)
                # Add more frequencies as needed (weekly, monthly, etc.)
        
        # Save changes to the reminders
        if overdue_reminders:
            self.save_health_data()
        
        return overdue_reminders
        
    def shutdown(self) -> None:
        """Graceful shutdown"""
        self.save_health_data()

# =============================================================================
# CLI Test
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("Running HealthAssistant module test...")
    assistant = HealthAssistant()
    
    # Add a new wellness goal
    target_date = datetime.now() + timedelta(days=90)
    print(assistant.add_wellness_goal("Run 5k", "5 km", "fitness", target_date))
    
    # Add a health metric
    print(assistant.add_health_metric("weight", "75", "kg"))

    # Add a daily reminder
    print(assistant.add_health_reminder("Take vitamins", "Daily vitamin supplement", "daily", "medication"))

    # Get a random health tip
    print("\nHere's a health tip:")
    print(assistant.get_health_tip("nutrition"))

    # Check for overdue reminders (will not trigger on first run)
    print("\nChecking for overdue reminders...")
    overdue = assistant.get_overdue_reminders()
    if overdue:
        for r in overdue:
            print(f"Overdue reminder: {r.title}")
    else:
        print("No reminders are currently overdue.")
