#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
💎 GEM OS - Health Assistant
Comprehensive health and wellness features for users
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
class MedicationReminder:
    """Medication reminder data."""
    id: Optional[int] = None
    name: str = ""
    dosage: str = ""
    frequency: str = ""  # daily, twice_daily, weekly, etc.
    times: List[str] = None  # ["08:00", "20:00"]
    start_date: str = ""
    end_date: Optional[str] = None
    notes: str = ""
    is_active: bool = True
    
    def __post_init__(self):
        if self.times is None:
            self.times = []


@dataclass
class HealthMetric:
    """Health metric measurement."""
    id: Optional[int] = None
    metric_type: str = ""  # blood_pressure, weight, glucose, etc.
    value: float = 0.0
    unit: str = ""
    timestamp: str = ""
    notes: str = ""


@dataclass
class WellnessGoal:
    """Wellness goal tracking."""
    id: Optional[int] = None
    goal_type: str = ""  # exercise, water, sleep, etc.
    target_value: float = 0.0
    current_value: float = 0.0
    unit: str = ""
    frequency: str = "daily"  # daily, weekly, monthly
    start_date: str = ""
    is_active: bool = True


class HealthDatabase:
    """Health data storage and management."""
    
    def __init__(self, db_path: Path, logger: logging.Logger):
        self.db_path = db_path
        self.logger = logger
        self._init_database()
    
    def _init_database(self):
        """Initialize health database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Medication reminders table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS medication_reminders (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        dosage TEXT,
                        frequency TEXT,
                        times TEXT,  -- JSON array
                        start_date TEXT,
                        end_date TEXT,
                        notes TEXT,
                        is_active BOOLEAN DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Health metrics table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS health_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        metric_type TEXT NOT NULL,
                        value REAL NOT NULL,
                        unit TEXT,
                        timestamp TEXT,
                        notes TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Wellness goals table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS wellness_goals (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        goal_type TEXT NOT NULL,
                        target_value REAL,
                        current_value REAL DEFAULT 0,
                        unit TEXT,
                        frequency TEXT DEFAULT 'daily',
                        start_date TEXT,
                        is_active BOOLEAN DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Medication log table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS medication_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        reminder_id INTEGER,
                        taken_at TIMESTAMP,
                        status TEXT,  -- taken, missed, delayed
                        notes TEXT,
                        FOREIGN KEY (reminder_id) REFERENCES medication_reminders (id)
                    )
                ''')
                
                conn.commit()
                self.logger.info("Health database initialized")
        
        except Exception as e:
            self.logger.error(f"Database initialization error: {e}")
    
    def add_medication_reminder(self, reminder: MedicationReminder) -> int:
        """Add medication reminder."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO medication_reminders 
                    (name, dosage, frequency, times, start_date, end_date, notes, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    reminder.name, reminder.dosage, reminder.frequency,
                    json.dumps(reminder.times), reminder.start_date,
                    reminder.end_date, reminder.notes, reminder.is_active
                ))
                conn.commit()
                return cursor.lastrowid
        
        except Exception as e:
            self.logger.error(f"Error adding medication reminder: {e}")
            return 0
    
    def get_active_medication_reminders(self) -> List[MedicationReminder]:
        """Get active medication reminders."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, name, dosage, frequency, times, start_date, end_date, notes, is_active
                    FROM medication_reminders 
                    WHERE is_active = 1
                ''')
                
                reminders = []
                for row in cursor.fetchall():
                    reminder = MedicationReminder(
                        id=row[0], name=row[1], dosage=row[2], frequency=row[3],
                        times=json.loads(row[4]) if row[4] else [],
                        start_date=row[5], end_date=row[6], notes=row[7], is_active=bool(row[8])
                    )
                    reminders.append(reminder)
                
                return reminders
        
        except Exception as e:
            self.logger.error(f"Error getting medication reminders: {e}")
            return []
    
    def log_medication_taken(self, reminder_id: int, status: str = "taken", notes: str = ""):
        """Log medication as taken."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO medication_log (reminder_id, taken_at, status, notes)
                    VALUES (?, ?, ?, ?)
                ''', (reminder_id, datetime.now().isoformat(), status, notes))
                conn.commit()
        
        except Exception as e:
            self.logger.error(f"Error logging medication: {e}")
    
    def add_health_metric(self, metric: HealthMetric) -> int:
        """Add health metric."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO health_metrics (metric_type, value, unit, timestamp, notes)
                    VALUES (?, ?, ?, ?, ?)
                ''', (metric.metric_type, metric.value, metric.unit, metric.timestamp, metric.notes))
                conn.commit()
                return cursor.lastrowid
        
        except Exception as e:
            self.logger.error(f"Error adding health metric: {e}")
            return 0
    
    def get_recent_health_metrics(self, metric_type: str, days: int = 30) -> List[HealthMetric]:
        """Get recent health metrics."""
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, metric_type, value, unit, timestamp, notes
                    FROM health_metrics 
                    WHERE metric_type = ? AND timestamp >= ?
                    ORDER BY timestamp DESC
                ''', (metric_type, cutoff_date))
                
                metrics = []
                for row in cursor.fetchall():
                    metric = HealthMetric(
                        id=row[0], metric_type=row[1], value=row[2],
                        unit=row[3], timestamp=row[4], notes=row[5]
                    )
                    metrics.append(metric)
                
                return metrics
        
        except Exception as e:
            self.logger.error(f"Error getting health metrics: {e}")
            return []


class MedicationManager:
    """Medication reminder management."""
    
    def __init__(self, database: HealthDatabase, logger: logging.Logger):
        self.database = database
        self.logger = logger
        self.active_reminders: List[MedicationReminder] = []
        self.reminder_callbacks: List[callable] = []
        
        # Load active reminders
        self._load_active_reminders()
        
        # Schedule reminder checks
        self._schedule_reminder_checks()
    
    def _load_active_reminders(self):
        """Load active medication reminders."""
        self.active_reminders = self.database.get_active_medication_reminders()
        self.logger.info(f"Loaded {len(self.active_reminders)} active medication reminders")
    
    def _schedule_reminder_checks(self):
        """Schedule periodic reminder checks."""
        schedule.every().minute.do(self._check_reminders)
    
    def _check_reminders(self):
        """Check if any reminders are due."""
        current_time = datetime.now().strftime("%H:%M")
        current_date = datetime.now().date()
        
        for reminder in self.active_reminders:
            if current_time in reminder.times:
                # Check if reminder should be active today
                start_date = datetime.fromisoformat(reminder.start_date).date()
                
                if current_date >= start_date:
                    if not reminder.end_date or current_date <= datetime.fromisoformat(reminder.end_date).date():
                        # Trigger reminder
                        asyncio.create_task(self._trigger_reminder(reminder))
    
    async def _trigger_reminder(self, reminder: MedicationReminder):
        """Trigger medication reminder."""
        message = f"Hora do medicamento: {reminder.name}"
        if reminder.dosage:
            message += f", {reminder.dosage}"
        
        self.logger.info(f"Medication reminder: {message}")
        
        # Call registered callbacks
        for callback in self.reminder_callbacks:
            try:
                await callback(reminder, message)
            except Exception as e:
                self.logger.error(f"Reminder callback error: {e}")
    
    def add_reminder_callback(self, callback: callable):
        """Add reminder callback."""
        self.reminder_callbacks.append(callback)
    
    async def add_medication(self, name: str, dosage: str, times: List[str], 
                           frequency: str = "daily", notes: str = "") -> str:
        """Add new medication reminder."""
        try:
            reminder = MedicationReminder(
                name=name,
                dosage=dosage,
                frequency=frequency,
                times=times,
                start_date=datetime.now().isoformat(),
                notes=notes
            )
            
            reminder_id = self.database.add_medication_reminder(reminder)
            
            if reminder_id:
                reminder.id = reminder_id
                self.active_reminders.append(reminder)
                
                times_str = ", ".join(times)
                return f"Lembrete de medicamento adicionado: {name} às {times_str}"
            else:
                return "Erro ao adicionar lembrete de medicamento"
        
        except Exception as e:
            self.logger.error(f"Error adding medication: {e}")
            return "Erro ao adicionar medicamento"
    
    async def mark_medication_taken(self, medication_name: str) -> str:
        """Mark medication as taken."""
        try:
            for reminder in self.active_reminders:
                if reminder.name.lower() == medication_name.lower():
                    self.database.log_medication_taken(reminder.id, "taken")
                    return f"Medicamento {medication_name} marcado como tomado"
            
            return f"Medicamento {medication_name} não encontrado"
        
        except Exception as e:
            self.logger.error(f"Error marking medication taken: {e}")
            return "Erro ao marcar medicamento"
    
    def get_todays_medications(self) -> List[Tuple[str, str]]:
        """Get today's medication schedule."""
        medications = []
        
        for reminder in self.active_reminders:
            for time in reminder.times:
                medications.append((time, f"{reminder.name} - {reminder.dosage}"))
        
        # Sort by time
        medications.sort(key=lambda x: x[0])
        return medications


class HealthTracker:
    """Health metrics tracking."""
    
    def __init__(self, database: HealthDatabase, logger: logging.Logger):
        self.database = database
        self.logger = logger
    
    async def record_blood_pressure(self, systolic: int, diastolic: int, notes: str = "") -> str:
        """Record blood pressure measurement."""
        try:
            metric = HealthMetric(
                metric_type="blood_pressure",
                value=float(f"{systolic}.{diastolic:02d}"),  # Store as 120.80
                unit="mmHg",
                timestamp=datetime.now().isoformat(),
                notes=notes
            )
            
            metric_id = self.database.add_health_metric(metric)
            
            if metric_id:
                # Provide feedback on reading
                feedback = self._analyze_blood_pressure(systolic, diastolic)
                return f"Pressão arterial registrada: {systolic}/{diastolic} mmHg. {feedback}"
            else:
                return "Erro ao registrar pressão arterial"
        
        except Exception as e:
            self.logger.error(f"Error recording blood pressure: {e}")
            return "Erro ao registrar pressão arterial"
    
    def _analyze_blood_pressure(self, systolic: int, diastolic: int) -> str:
        """Analyze blood pressure reading."""
        if systolic < 120 and diastolic < 80:
            return "Pressão normal."
        elif systolic < 130 and diastolic < 80:
            return "Pressão ligeiramente elevada."
        elif systolic < 140 or diastolic < 90:
            return "Hipertensão estágio 1. Considere consultar um médico."
        else:
            return "Hipertensão estágio 2. Procure atendimento médico."
    
    async def record_weight(self, weight: float, unit: str = "kg", notes: str = "") -> str:
        """Record weight measurement."""
        try:
            metric = HealthMetric(
                metric_type="weight",
                value=weight,
                unit=unit,
                timestamp=datetime.now().isoformat(),
                notes=notes
            )
            
            metric_id = self.database.add_health_metric(metric)
            
            if metric_id:
                return f"Peso registrado: {weight} {unit}"
            else:
                return "Erro ao registrar peso"
        
        except Exception as e:
            self.logger.error(f"Error recording weight: {e}")
            return "Erro ao registrar peso"
    
    async def record_glucose(self, glucose: float, unit: str = "mg/dL", notes: str = "") -> str:
        """Record glucose measurement."""
        try:
            metric = HealthMetric(
                metric_type="glucose",
                value=glucose,
                unit=unit,
                timestamp=datetime.now().isoformat(),
                notes=notes
            )
            
            metric_id = self.database.add_health_metric(metric)
            
            if metric_id:
                feedback = self._analyze_glucose(glucose)
                return f"Glicose registrada: {glucose} {unit}. {feedback}"
            else:
                return "Erro ao registrar glicose"
        
        except Exception as e:
            self.logger.error(f"Error recording glucose: {e}")
            return "Erro ao registrar glicose"
    
    def _analyze_glucose(self, glucose: float) -> str:
        """Analyze glucose reading."""
        if glucose < 70:
            return "Glicose baixa. Considere consumir algo doce."
        elif glucose <= 100:
            return "Glicose normal."
        elif glucose <= 125:
            return "Glicose ligeiramente elevada."
        else:
            return "Glicose alta. Consulte seu médico."
    
    async def get_health_summary(self, days: int = 7) -> str:
        """Get health summary for recent days."""
        try:
            summary = f"Resumo de saúde dos últimos {days} dias:\n\n"
            
            # Blood pressure
            bp_metrics = self.database.get_recent_health_metrics("blood_pressure", days)
            if bp_metrics:
                latest_bp = bp_metrics[0]
                systolic = int(latest_bp.value)
                diastolic = int((latest_bp.value % 1) * 100)
                summary += f"Pressão arterial: {systolic}/{diastolic} mmHg (última medição)\n"
            
            # Weight
            weight_metrics = self.database.get_recent_health_metrics("weight", days)
            if weight_metrics:
                latest_weight = weight_metrics[0]
                summary += f"Peso: {latest_weight.value} {latest_weight.unit} (última medição)\n"
            
            # Glucose
            glucose_metrics = self.database.get_recent_health_metrics("glucose", days)
            if glucose_metrics:
                latest_glucose = glucose_metrics[0]
                summary += f"Glicose: {latest_glucose.value} {latest_glucose.unit} (última medição)\n"
            
            if not any([bp_metrics, weight_metrics, glucose_metrics]):
                summary += "Nenhuma medição registrada no período."
            
            return summary
        
        except Exception as e:
            self.logger.error(f"Error getting health summary: {e}")
            return "Erro ao gerar resumo de saúde"


class WellnessReminders:
    """Wellness and lifestyle reminders."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.reminder_callbacks: List[callable] = []
        
        # Schedule wellness reminders
        self._schedule_wellness_reminders()
    
    def _schedule_wellness_reminders(self):
        """Schedule wellness reminders."""
        # Water reminders every 2 hours
        schedule.every(2).hours.do(self._water_reminder)
        
        # Posture reminder every hour
        schedule.every().hour.do(self._posture_reminder)
        
        # Exercise reminder daily at 9 AM
        schedule.every().day.at("09:00").do(self._exercise_reminder)
        
        # Break reminder every 30 minutes during work hours
        schedule.every(30).minutes.do(self._break_reminder)
    
    async def _water_reminder(self):
        """Water intake reminder."""
        message = "Lembre-se de beber água! Manter-se hidratado é importante para sua saúde."
        await self._trigger_wellness_reminder("water", message)
    
    async def _posture_reminder(self):
        """Posture reminder."""
        message = "Verifique sua postura. Mantenha as costas retas e os ombros relaxados."
        await self._trigger_wellness_reminder("posture", message)
    
    async def _exercise_reminder(self):
        """Exercise reminder."""
        message = "Que tal fazer alguns exercícios hoje? Mesmo uma caminhada curta faz bem!"
        await self._trigger_wellness_reminder("exercise", message)
    
    async def _break_reminder(self):
        """Break reminder during work hours."""
        current_hour = datetime.now().hour
        
        # Only during typical work hours
        if 9 <= current_hour <= 17:
            message = "Hora de fazer uma pausa! Descanse os olhos e alongue-se um pouco."
            await self._trigger_wellness_reminder("break", message)
    
    async def _trigger_wellness_reminder(self, reminder_type: str, message: str):
        """Trigger wellness reminder."""
        self.logger.info(f"Wellness reminder ({reminder_type}): {message}")
        
        # Call registered callbacks
        for callback in self.reminder_callbacks:
            try:
                await callback(reminder_type, message)
            except Exception as e:
                self.logger.error(f"Wellness reminder callback error: {e}")
    
    def add_reminder_callback(self, callback: callable):
        """Add wellness reminder callback."""
        self.reminder_callbacks.append(callback)


class HealthAssistant:
    """Main health assistant manager."""
    
    def __init__(self, gem_assistant, logger: Optional[logging.Logger] = None):
        self.gem = gem_assistant
        self.logger = logger or logging.getLogger("HealthAssistant")
        
        # Initialize database
        db_path = Path.home() / ".gem" / "data" / "health.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.database = HealthDatabase(db_path, self.logger)
        
        # Initialize components
        self.medication_manager = MedicationManager(self.database, self.logger)
        self.health_tracker = HealthTracker(self.database, self.logger)
        self.wellness_reminders = WellnessReminders(self.logger)
        
        # Settings
        self.reminders_enabled = True
        self.voice_reminders = True
    
    async def initialize(self):
        """Initialize health assistant."""
        self.logger.info("Initializing health assistant...")
        
        # Register callbacks
        self.medication_manager.add_reminder_callback(self._handle_medication_reminder)
        self.wellness_reminders.add_reminder_callback(self._handle_wellness_reminder)
        
        # Start scheduler
        asyncio.create_task(self._run_scheduler())
        
        self.logger.info("Health assistant initialized")
    
    async def _run_scheduler(self):
        """Run the reminder scheduler."""
        while True:
            try:
                schedule.run_pending()
                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                self.logger.error(f"Scheduler error: {e}")
                await asyncio.sleep(60)
    
    async def _handle_medication_reminder(self, reminder: MedicationReminder, message: str):
        """Handle medication reminder."""
        if self.reminders_enabled and self.voice_reminders and self.gem.tts_module:
            await self.gem.tts_module.speak(message)
    
    async def _handle_wellness_reminder(self, reminder_type: str, message: str):
        """Handle wellness reminder."""
        if self.reminders_enabled and self.voice_reminders and self.gem.tts_module:
            await self.gem.tts_module.speak(message)
    
    async def setup_medication_reminder(self) -> str:
        """Interactive medication reminder setup."""
        return ("Para configurar um lembrete de medicamento, diga: "
                "'lembrar medicamento [nome] às [horário]'. "
                "Por exemplo: 'lembrar medicamento aspirina às 8 horas'")
    
    async def add_medication(self, name: str, times: List[str], dosage: str = "") -> str:
        """Add medication reminder."""
        return await self.medication_manager.add_medication(name, dosage, times)
    
    async def mark_medication_taken(self, medication_name: str) -> str:
        """Mark medication as taken."""
        return await self.medication_manager.mark_medication_taken(medication_name)
    
    async def record_blood_pressure(self, systolic: int, diastolic: int) -> str:
        """Record blood pressure."""
        return await self.health_tracker.record_blood_pressure(systolic, diastolic)
    
    async def record_weight(self, weight: float) -> str:
        """Record weight."""
        return await self.health_tracker.record_weight(weight)
    
    async def record_glucose(self, glucose: float) -> str:
        """Record glucose."""
        return await self.health_tracker.record_glucose(glucose)
    
    async def get_health_status(self) -> str:
        """Get comprehensive health status."""
        try:
            status = "Status de saúde:\n\n"
            
            # Today's medications
            todays_meds = self.medication_manager.get_todays_medications()
            if todays_meds:
                status += "Medicamentos de hoje:\n"
                for time, medication in todays_meds:
                    status += f"- {time}: {medication}\n"
                status += "\n"
            
            # Health summary
            health_summary = await self.health_tracker.get_health_summary()
            status += health_summary
            
            return status
        
        except Exception as e:
            self.logger.error(f"Error getting health status: {e}")
            return "Erro ao obter status de saúde"
    
    async def get_medication_schedule(self) -> str:
        """Get today's medication schedule."""
        try:
            todays_meds = self.medication_manager.get_todays_medications()
            
            if not todays_meds:
                return "Nenhum medicamento agendado para hoje."
            
            schedule_text = "Medicamentos de hoje:\n"
            for time, medication in todays_meds:
                schedule_text += f"- {time}: {medication}\n"
            
            return schedule_text
        
        except Exception as e:
            self.logger.error(f"Error getting medication schedule: {e}")
            return "Erro ao obter cronograma de medicamentos"
    
    def enable_reminders(self, enabled: bool = True):
        """Enable/disable health reminders."""
        self.reminders_enabled = enabled
        self.logger.info(f"Health reminders {'enabled' if enabled else 'disabled'}")
    
    def enable_voice_reminders(self, enabled: bool = True):
        """Enable/disable voice reminders."""
        self.voice_reminders = enabled
        self.logger.info(f"Voice reminders {'enabled' if enabled else 'disabled'}")
    
    async def emergency_health_info(self) -> str:
        """Provide emergency health information."""
        info = ("Em caso de emergência médica, ligue 192 (SAMU) ou 193 (Bombeiros). "
                "Para intoxicação, ligue 0800 722 6001 (Centro de Informação Toxicológica). "
                "Mantenha sempre seus medicamentos e informações médicas atualizados.")
        
        if self.gem.tts_module:
            await self.gem.tts_module.speak(info)
        
        return info