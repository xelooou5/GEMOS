#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
üíé GEM OS - Health Manager (core/health_manager.py)
Manages user's health and wellness data, including tracking metrics, medication reminders, and workout logs.

Responsibilities
----------------
- Track and record various health metrics (e.g., weight, water intake, steps).
- Manage medication reminders.
- Log workout sessions and physical activities.
- Persist health data using the Storage module.
- Expose health management capabilities as tools for the LLM.
- Publish health-related events.
- Integrate with NotificationManager for alerts and reminders.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable, Awaitable
from collections import defaultdict

from core.plugins import BasePlugin, CommandExecutor, GEMVoiceAssistant
from core.notification_manager import NotificationManager, NOTIFICATION_INFO, NOTIFICATION_WARNING, NOTIFICATION_SUCCESS, NOTIFICATION_ERROR

# Forward declarations for type hinting
class EventManager:
    async def publish(self, event_type: str, data: Optional[Dict[str, Any]] = None) -> None:
        pass

class TTSModule:
    async def speak(self, text: str) -> None:
        pass

class ConfigManager:
    def get_config(self) -> Any:
        pass

class Storage:
    async def get_setting(self, key: str, default: Any = None) -> Any:
        pass
    async def set_setting(self, key: str, value: Any) -> bool:
        pass

# --- Dataclass para M√©trica de Sa√∫de ---
@dataclass
class HealthMetric:
    id: str
    name: str # Ex: "peso", "√°gua", "passos"
    value: float
    unit: str # Ex: "kg", "litros", "passos"
    timestamp: datetime = field(default_factory=datetime.now)
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "value": self.value,
            "unit": self.unit,
            "timestamp": self.timestamp.isoformat(),
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> HealthMetric:
        return cls(
            id=data["id"],
            name=data["name"],
            value=data["value"],
            unit=data["unit"],
            timestamp=datetime.fromisoformat(data["timestamp"]) if data.get("timestamp") else datetime.now(),
            notes=data.get("notes"),
        )

# --- Dataclass para Lembrete de Medica√ß√£o ---
@dataclass
class MedicationReminder:
    id: str
    medication_name: str
    dosage: str
    schedule_time: str # HH:MM
    last_taken: Optional[datetime] = None
    is_enabled: bool = True
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "medication_name": self.medication_name,
            "dosage": self.dosage,
            "schedule_time": self.schedule_time,
            "last_taken": self.last_taken.isoformat() if self.last_taken else None,
            "is_enabled": self.is_enabled,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MedicationReminder:
        return cls(
            id=data["id"],
            medication_name=data["medication_name"],
            dosage=data["dosage"],
            schedule_time=data["schedule_time"],
            last_taken=datetime.fromisoformat(data["last_taken"]) if data.get("last_taken") else None,
            is_enabled=data.get("is_enabled", True),
            notes=data.get("notes"),
        )

# --- Dataclass para Registo de Exerc√≠cios ---
@dataclass
class WorkoutLog:
    id: str
    activity_type: str # Ex: "corrida", "caminhada", "muscula√ß√£o"
    duration_minutes: float
    calories_burned: Optional[float] = None
    distance_km: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "activity_type": self.activity_type,
            "duration_minutes": self.duration_minutes,
            "calories_burned": self.calories_burned,
            "distance_km": self.distance_km,
            "timestamp": self.timestamp.isoformat(),
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> WorkoutLog:
        return cls(
            id=data["id"],
            activity_type=data["activity_type"],
            duration_minutes=data["duration_minutes"],
            calories_burned=data.get("calories_burned"),
            distance_km=data.get("distance_km"),
            timestamp=datetime.fromisoformat(data["timestamp"]) if data.get("timestamp") else datetime.now(),
            notes=data.get("notes"),
        )

# --- Health Manager como um Plugin ---
class HealthManager(BasePlugin):
    """
    Manages user's health and wellness data for GEM OS, acting as a plugin.
    """
    STORAGE_KEY_HEALTH_METRICS = "user_health_metrics"
    STORAGE_KEY_MEDICATION_REMINDERS = "user_medication_reminders"
    STORAGE_KEY_WORKOUT_LOGS = "user_workout_logs"

    def __init__(self, gem_instance: GEMVoiceAssistant, logger: Optional[logging.Logger] = None):
        super().__init__(gem_instance, logger)
        self.logger.info("HealthManager plugin inicializado.")
        
        self.event_manager: EventManager = gem_instance.event_manager
        self.notification_manager: NotificationManager = gem_instance.notification_manager
        self.storage: Storage = gem_instance.storage
        self.tts_module: TTSModule = gem_instance.tts_module

        self._health_metrics: Dict[str, HealthMetric] = {} # {id: metric_obj}
        self._medication_reminders: Dict[str, MedicationReminder] = {} # {id: reminder_obj}
        self._workout_logs: Dict[str, WorkoutLog] = {} # {id: workout_obj}
        self._data_loaded = asyncio.Event()

        self._medication_check_task: Optional[asyncio.Task] = None
        self._medication_check_interval_seconds: int = 60 # Check every minute

    async def initialize(self) -> None:
        """Loads health data from storage and starts background reminder checker."""
        await self._load_data_from_storage()
        if not self._medication_check_task:
            self._medication_check_task = asyncio.create_task(self._periodic_medication_check())
            self.logger.info("Verifica√ß√£o peri√≥dica de medica√ß√£o iniciada.")
        self.event_manager.subscribe("GEM_SHUTDOWN", self._on_gem_shutdown)
        self.logger.info("HealthManager inicializado.")

    async def _on_gem_shutdown(self, event_data: Dict[str, Any]) -> None:
        """Handler for GEM_SHUTDOWN event to gracefully stop background tasks."""
        self.logger.info("Recebido GEM_SHUTDOWN. A parar as verifica√ß√µes de medica√ß√£o.")
        self.shutdown()

    async def _load_data_from_storage(self) -> None:
        """Loads all health-related data from persistent storage."""
        try:
            metrics_data = await self.storage.get_setting(self.STORAGE_KEY_HEALTH_METRICS, [])
            for item_dict in metrics_data:
                try:
                    item = HealthMetric.from_dict(item_dict)
                    self._health_metrics[item.id] = item
                except Exception as e:
                    self.logger.error(f"Erro ao carregar m√©trica de sa√∫de: {e} - Dados: {item_dict}", exc_info=True)
            self.logger.info(f"Carregadas {len(self._health_metrics)} m√©tricas de sa√∫de.")

            reminders_data = await self.storage.get_setting(self.STORAGE_KEY_MEDICATION_REMINDERS, [])
            for item_dict in reminders_data:
                try:
                    item = MedicationReminder.from_dict(item_dict)
                    self._medication_reminders[item.id] = item
                except Exception as e:
                    self.logger.error(f"Erro ao carregar lembrete de medica√ß√£o: {e} - Dados: {item_dict}", exc_info=True)
            self.logger.info(f"Carregados {len(self._medication_reminders)} lembretes de medica√ß√£o.")

            workouts_data = await self.storage.get_setting(self.STORAGE_KEY_WORKOUT_LOGS, [])
            for item_dict in workouts_data:
                try:
                    item = WorkoutLog.from_dict(item_dict)
                    self._workout_logs[item.id] = item
                except Exception as e:
                    self.logger.error(f"Erro ao carregar registo de exerc√≠cio: {e} - Dados: {item_dict}", exc_info=True)
            self.logger.info(f"Carregados {len(self._workout_logs)} registos de exerc√≠cios.")

        except Exception as e:
            self.logger.error(f"Falha ao carregar dados de sa√∫de: {e}", exc_info=True)
        finally:
            self._data_loaded.set() # Sinaliza que os dados foram carregados

    async def _save_health_metrics_to_storage(self) -> None:
        """Saves current health metrics to persistent storage."""
        try:
            data = [item.to_dict() for item in self._health_metrics.values()]
            await self.storage.set_setting(self.STORAGE_KEY_HEALTH_METRICS, data)
            self.logger.debug(f"Salvas {len(self._health_metrics)} m√©tricas de sa√∫de.")
        except Exception as e:
            self.logger.error(f"Falha ao salvar m√©tricas de sa√∫de: {e}", exc_info=True)

    async def _save_medication_reminders_to_storage(self) -> None:
        """Saves current medication reminders to persistent storage."""
        try:
            data = [item.to_dict() for item in self._medication_reminders.values()]
            await self.storage.set_setting(self.STORAGE_KEY_MEDICATION_REMINDERS, data)
            self.logger.debug(f"Salvos {len(self._medication_reminders)} lembretes de medica√ß√£o.")
        except Exception as e:
            self.logger.error(f"Falha ao salvar lembretes de medica√ß√£o: {e}", exc_info=True)

    async def _save_workout_logs_to_storage(self) -> None:
        """Saves current workout logs to persistent storage."""
        try:
            data = [item.to_dict() for item in self._workout_logs.values()]
            await self.storage.set_setting(self.STORAGE_KEY_WORKOUT_LOGS, data)
            self.logger.debug(f"Salvos {len(self._workout_logs)} registos de exerc√≠cios.")
        except Exception as e:
            self.logger.error(f"Falha ao salvar registos de exerc√≠cios: {e}", exc_info=True)

    async def _periodic_medication_check(self) -> None:
        """Periodically checks for medication reminders and notifies the user."""
        self.logger.debug("Loop de verifica√ß√£o peri√≥dica de medica√ß√£o iniciado.")
        await self._data_loaded.wait() # Wait until data is loaded
        while True:
            try:
                await self._check_medication_reminders()
                await asyncio.sleep(self._medication_check_interval_seconds)
            except asyncio.CancelledError:
                self.logger.info("Tarefa de verifica√ß√£o peri√≥dica de medica√ß√£o cancelada.")
                break
            except Exception as e:
                self.logger.error(f"Erro no loop de verifica√ß√£o de medica√ß√£o: {e}", exc_info=True)
                await asyncio.sleep(self._medication_check_interval_seconds * 2) # Wait longer on error

    async def _check_medication_reminders(self) -> None:
        """Checks for active medication reminders and triggers notifications."""
        now = datetime.now()
        current_time_str = now.strftime("%H:%M")

        for reminder_id, reminder in list(self._medication_reminders.items()):
            if reminder.is_enabled and reminder.schedule_time == current_time_str:
                # Evitar m√∫ltiplos lembretes no mesmo minuto, verificar se j√° foi lembrado hoje
                if reminder.last_taken and reminder.last_taken.date() == now.date() and reminder.last_taken.hour == now.hour and reminder.last_taken.minute == now.minute:
                    continue # J√° lembramos neste minuto

                message = f"Lembrete de medica√ß√£o: √â hora de tomar {reminder.dosage} de {reminder.medication_name}."
                await self.notification_manager.add_notification(message, level=NOTIFICATION_WARNING, vocalize=True)
                await self.tts_module.speak(message)
                self.logger.info(f"Lembrete enviado para medica√ß√£o '{reminder.medication_name}'.")
                await self.event_manager.publish("HEALTH_MEDICATION_REMINDER_TRIGGERED", reminder.to_dict())

                reminder.last_taken = now # Atualizar para evitar repeti√ß√£o excessiva
                await self._save_medication_reminders_to_storage()


    # --------------------------------------------------------------------- Commands (Health Metrics)

    async def _add_health_metric_command(self, name: str, value: float, unit: str,
                                         timestamp: Optional[str] = None, notes: Optional[str] = None) -> Dict[str, Any]:
        """
        Adiciona uma nova m√©trica de sa√∫de (ex: peso, consumo de √°gua, passos).
        `timestamp` deve ser uma string no formato ISO 8601 (YYYY-MM-DD HH:MM).
        """
        await self._data_loaded.wait()

        parsed_timestamp: datetime = datetime.now()
        if timestamp:
            try:
                parsed_timestamp = datetime.fromisoformat(timestamp)
            except ValueError:
                await self._speak_response("Formato de data/hora inv√°lido. Por favor, use 'AAAA-MM-DD HH:MM'.")
                return {"success": False, "output": "Formato de data/hora inv√°lido.", "error": "Invalid datetime format"}

        metric_id = str(uuid.uuid4())
        new_metric = HealthMetric(
            id=metric_id,
            name=name,
            value=value,
            unit=unit,
            timestamp=parsed_timestamp,
            notes=notes
        )
        self._health_metrics[metric_id] = new_metric
        await self._save_health_metrics_to_storage()
        
        message = f"M√©trica '{name}' ({value} {unit}) registada com sucesso."
        await self._speak_response(message)
        await self.notification_manager.add_notification(message, level=NOTIFICATION_SUCCESS)
        await self.event_manager.publish("HEALTH_METRIC_ADDED", new_metric.to_dict())
        self.logger.info(message)
        return {"success": True, "output": message, "error": None}

    async def _list_health_metrics_command(self, name: Optional[str] = None, limit: int = 5) -> Dict[str, Any]:
        """
        Lista m√©tricas de sa√∫de registadas, opcionalmente filtrando por nome da m√©trica.
        Retorna as mais recentes primeiro.
        """
        await self._data_loaded.wait()

        filtered_metrics: List[HealthMetric] = []
        for metric in self._health_metrics.values():
            if name is None or metric.name.lower() == name.lower():
                filtered_metrics.append(metric)
        
        filtered_metrics.sort(key=lambda m: m.timestamp, reverse=True) # Mais recentes primeiro
        metrics_to_display = filtered_metrics[:limit]

        if not metrics_to_display:
            message = f"Nenhuma m√©trica de sa√∫de '{name}' encontrada." if name else "Nenhuma m√©trica de sa√∫de encontrada."
            await self._speak_response(message)
            return {"success": True, "output": message, "error": None}
        
        output_lines = [f"M√©tricas de Sa√∫de ({name or 'Todas'}, mais recentes):"]
        for i, metric in enumerate(metrics_to_display):
            output_lines.append(f"{i+1}. {metric.name.capitalize()}: {metric.value} {metric.unit} (em {metric.timestamp.strftime('%Y-%m-%d %H:%M')})")
            if metric.notes:
                output_lines.append(f"   Notas: {metric.notes}")
            output_lines.append(f"   (ID: {metric.id[:8]}...)")
            output_lines.append("-" * 20)
        
        message = "\n".join(output_lines)
        await self._speak_response(f"M√©tricas de sa√∫de listadas. Verifique o ecr√£ para os detalhes.")
        await self.notification_manager.add_notification("M√©tricas de sa√∫de exibidas.", level=NOTIFICATION_INFO)
        return {"success": True, "output": message, "error": None}

    # --------------------------------------------------------------------- Commands (Medication Reminders)

    async def _add_medication_reminder_command(self, medication_name: str, dosage: str, schedule_time: str,
                                               notes: Optional[str] = None, is_enabled: bool = True) -> Dict[str, Any]:
        """
        Adiciona um novo lembrete de medica√ß√£o.
        `schedule_time` deve ser no formato HH:MM.
        """
        await self._data_loaded.wait()

        try:
            datetime.strptime(schedule_time, "%H:%M") # Validar formato da hora
        except ValueError:
            await self._speak_response("Formato de hora inv√°lido para o agendamento. Use 'HH:MM'.")
            return {"success": False, "output": "Formato de hora inv√°lido.", "error": "Invalid time format"}

        reminder_id = str(uuid.uuid4())
        new_reminder = MedicationReminder(
            id=reminder_id,
            medication_name=medication_name,
            dosage=dosage,
            schedule_time=schedule_time,
            is_enabled=is_enabled,
            notes=notes
        )
        self._medication_reminders[reminder_id] = new_reminder
        await self._save_medication_reminders_to_storage()

        message = f"Lembrete para '{medication_name}' ({dosage}) agendado para {schedule_time}."
        await self._speak_response(message)
        await self.notification_manager.add_notification(message, level=NOTIFICATION_SUCCESS)
        await self.event_manager.publish("HEALTH_MEDICATION_REMINDER_ADDED", new_reminder.to_dict())
        self.logger.info(message)
        return {"success": True, "output": message, "error": None}

    async def _list_medication_reminders_command(self, is_enabled: Optional[bool] = None) -> Dict[str, Any]:
        """
        Lista lembretes de medica√ß√£o, opcionalmente filtrando por status (ativado/desativado).
        """
        await self._data_loaded.wait()

        filtered_reminders: List[MedicationReminder] = []
        for reminder in self._medication_reminders.values():
            if is_enabled is None or reminder.is_enabled == is_enabled:
                filtered_reminders.append(reminder)
        
        filtered_reminders.sort(key=lambda r: r.schedule_time) # Ordenar por hora

        if not filtered_reminders:
            status_str = "ativados" if is_enabled is True else "desativados" if is_enabled is False else "definidos"
            message = f"Nenhum lembrete de medica√ß√£o {status_str} encontrado."
            await self._speak_response(message)
            return {"success": True, "output": message, "error": None}
        
        output_lines = [f"Lembretes de Medica√ß√£o ({'Ativados' if is_enabled is True else 'Desativados' if is_enabled is False else 'Todos'}):"]
        for i, reminder in enumerate(filtered_reminders):
            status_text = "Ativado" if reminder.is_enabled else "Desativado"
            last_taken_str = f" √öltima Vez: {reminder.last_taken.strftime('%Y-%m-%d %H:%M')}" if reminder.last_taken else ""
            output_lines.append(f"{i+1}. {reminder.medication_name} ({reminder.dosage}) - Agendado para: {reminder.schedule_time} ({status_text}){last_taken_str}")
            if reminder.notes:
                output_lines.append(f"   Notas: {reminder.notes}")
            output_lines.append(f"   (ID: {reminder.id[:8]}...)")
            output_lines.append("-" * 20)
        
        message = "\n".join(output_lines)
        await self._speak_response(f"Lembretes de medica√ß√£o listados. Verifique o ecr√£ para os detalhes.")
        await self.notification_manager.add_notification("Lembretes de medica√ß√£o exibidos.", level=NOTIFICATION_INFO)
        return {"success": True, "output": message, "error": None}

    async def _toggle_medication_reminder_command(self, reminder_id_prefix: str, enable: bool) -> Dict[str, Any]:
        """
        Ativa ou desativa um lembrete de medica√ß√£o.
        Requer um prefixo do ID do lembrete.
        """
        await self._data_loaded.wait()

        reminder_to_toggle: Optional[MedicationReminder] = None
        matching_reminders = [r for r in self._medication_reminders.values() if r.id.startswith(reminder_id_prefix)]

        if len(matching_reminders) == 1:
            reminder_to_toggle = matching_reminders[0]
        elif len(matching_reminders) > 1:
            message = f"M√∫ltiplos lembretes correspondem ao ID '{reminder_id_prefix}'. Por favor, seja mais espec√≠fico."
            await self._speak_response(message)
            return {"success": False, "output": message, "error": "Multiple matches"}
        else:
            message = f"Nenhum lembrete de medica√ß√£o encontrado com o ID '{reminder_id_prefix}'."
            await self._speak_response(message)
            return {"success": False, "output": message, "error": "Reminder not found"}
        
        if reminder_to_toggle:
            reminder_to_toggle.is_enabled = enable
            await self._save_medication_reminders_to_storage()

            action = "ativado" if enable else "desativado"
            message = f"Lembrete para '{reminder_to_toggle.medication_name}' {action} com sucesso."
            await self._speak_response(message)
            await self.notification_manager.add_notification(message, level=NOTIFICATION_SUCCESS)
            await self.event_manager.publish("HEALTH_MEDICATION_REMINDER_TOGGLED", {"id": reminder_to_toggle.id, "enabled": enable})
            self.logger.info(message)
            return {"success": True, "output": message, "error": None}
        
        return {"success": False, "output": "Erro desconhecido ao alternar lembrete.", "error": "Unknown error"}

    async def _delete_medication_reminder_command(self, reminder_id_prefix: str) -> Dict[str, Any]:
        """
        Remove um lembrete de medica√ß√£o.
        Requer um prefixo do ID do lembrete.
        """
        await self._data_loaded.wait()

        reminder_to_delete: Optional[MedicationReminder] = None
        matching_reminders = [r for r in self._medication_reminders.values() if r.id.startswith(reminder_id_prefix)]

        if len(matching_reminders) == 1:
            reminder_to_delete = matching_reminders[0]
        elif len(matching_reminders) > 1:
            message = f"M√∫ltiplos lembretes correspondem ao ID '{reminder_id_prefix}'. Por favor, seja mais espec√≠fico."
            await self._speak_response(message)
            return {"success": False, "output": message, "error": "Multiple matches"}
        else:
            message = f"Nenhum lembrete de medica√ß√£o encontrado com o ID '{reminder_id_prefix}' para remo√ß√£o."
            await self._speak_response(message)
            return {"success": False, "output": message, "error": "Reminder not found"}

        if reminder_to_delete:
            del self._medication_reminders[reminder_to_delete.id]
            await self._save_medication_reminders_to_storage()
            message = f"Lembrete para '{reminder_to_delete.medication_name}' (ID: {reminder_to_delete.id[:8]}...) removido."
            await self._speak_response(message)
            await self.notification_manager.add_notification(message, level=NOTIFICATION_SUCCESS)
            await self.event_manager.publish("HEALTH_MEDICATION_REMINDER_DELETED", {"id": reminder_to_delete.id})
            self.logger.info(message)
            return {"success": True, "output": message, "error": None}
        
        return {"success": False, "output": "Erro desconhecido ao remover lembrete.", "error": "Unknown error"}


    # --------------------------------------------------------------------- Commands (Workout Logs)

    async def _add_workout_log_command(self, activity_type: str, duration_minutes: float,
                                       calories_burned: Optional[float] = None, distance_km: Optional[float] = None,
                                       timestamp: Optional[str] = None, notes: Optional[str] = None) -> Dict[str, Any]:
        """
        Adiciona um novo registo de exerc√≠cio.
        `timestamp` deve ser uma string no formato ISO 8601 (YYYY-MM-DD HH:MM).
        """
        await self._data_loaded.wait()

        parsed_timestamp: datetime = datetime.now()
        if timestamp:
            try:
                parsed_timestamp = datetime.fromisoformat(timestamp)
            except ValueError:
                await self._speak_response("Formato de data/hora inv√°lido. Por favor, use 'AAAA-MM-DD HH:MM'.")
                return {"success": False, "output": "Formato de data/hora inv√°lido.", "error": "Invalid datetime format"}

        if duration_minutes <= 0:
            await self._speak_response("A dura√ß√£o do exerc√≠cio deve ser positiva.")
            return {"success": False, "output": "Dura√ß√£o inv√°lida.", "error": "Duration must be positive"}

        workout_id = str(uuid.uuid4())
        new_workout = WorkoutLog(
            id=workout_id,
            activity_type=activity_type,
            duration_minutes=duration_minutes,
            calories_burned=calories_burned,
            distance_km=distance_km,
            timestamp=parsed_timestamp,
            notes=notes
        )
        self._workout_logs[workout_id] = new_workout
        await self._save_workout_logs_to_storage()

        message = f"Registo de exerc√≠cio '{activity_type}' ({duration_minutes} minutos) adicionado com sucesso."
        await self._speak_response(message)
        await self.notification_manager.add_notification(message, level=NOTIFICATION_SUCCESS)
        await self.event_manager.publish("HEALTH_WORKOUT_LOG_ADDED", new_workout.to_dict())
        self.logger.info(message)
        return {"success": True, "output": message, "error": None}

    async def _list_workout_logs_command(self, activity_type: Optional[str] = None, limit: int = 5) -> Dict[str, Any]:
        """
        Lista registos de exerc√≠cios, opcionalmente filtrando por tipo de atividade.
        Retorna os mais recentes primeiro.
        """
        await self._data_loaded.wait()

        filtered_workouts: List[WorkoutLog] = []
        for workout in self._workout_logs.values():
            if activity_type is None or workout.activity_type.lower() == activity_type.lower():
                filtered_workouts.append(workout)
        
        filtered_workouts.sort(key=lambda w: w.timestamp, reverse=True) # Mais recentes primeiro
        workouts_to_display = filtered_workouts[:limit]

        if not workouts_to_display:
            message = f"Nenhum registo de exerc√≠cio '{activity_type}' encontrado." if activity_type else "Nenhum registo de exerc√≠cio encontrado."
            await self._speak_response(message)
            return {"success": True, "output": message, "error": None}
        
        output_lines = [f"Registos de Exerc√≠cios ({activity_type or 'Todos'}, mais recentes):"]
        for i, workout in enumerate(workouts_to_display):
            calories_info = f", Queimou: {workout.calories_burned:.0f} cal" if workout.calories_burned else ""
            distance_info = f", Dist√¢ncia: {workout.distance_km:.2f} km" if workout.distance_km else ""
            output_lines.append(f"{i+1}. {workout.activity_type.capitalize()} - Dura√ß√£o: {workout.duration_minutes:.0f} min{calories_info}{distance_info} (em {workout.timestamp.strftime('%Y-%m-%d %H:%M')})")
            if workout.notes:
                output_lines.append(f"   Notas: {workout.notes}")
            output_lines.append(f"   (ID: {workout.id[:8]}...)")
            output_lines.append("-" * 20)
        
        message = "\n".join(output_lines)
        await self._speak_response(f"Registos de exerc√≠cios listados. Verifique o ecr√£ para os detalhes.")
        await self.notification_manager.add_notification("Registos de exerc√≠cios exibidos.", level=NOTIFICATION_INFO)
        return {"success": True, "output": message, "error": None}

    async def _delete_workout_log_command(self, workout_id_prefix: str) -> Dict[str, Any]:
        """
        Remove um registo de exerc√≠cio.
        Requer um prefixo do ID do registo.
        """
        await self._data_loaded.wait()

        workout_to_delete: Optional[WorkoutLog] = None
        matching_workouts = [w for w in self._workout_logs.values() if w.id.startswith(workout_id_prefix)]

        if len(matching_workouts) == 1:
            workout_to_delete = matching_workouts[0]
        elif len(matching_workouts) > 1:
            message = f"M√∫ltiplos registos de exerc√≠cios correspondem ao ID '{workout_id_prefix}'. Por favor, seja mais espec√≠fico."
            await self._speak_response(message)
            return {"success": False, "output": message, "error": "Multiple matches"}
        else:
            message = f"Nenhum registo de exerc√≠cio encontrado com o ID '{workout_id_prefix}' para remo√ß√£o."
            await self._speak_response(message)
            return {"success": False, "output": message, "error": "Workout log not found"}

        if workout_to_delete:
            del self._workout_logs[workout_to_delete.id]
            await self._save_workout_logs_to_storage()
            message = f"Registo de exerc√≠cio '{workout_to_delete.activity_type}' (ID: {workout_to_delete.id[:8]}...) removido."
            await self._speak_response(message)
            await self.notification_manager.add_notification(message, level=NOTIFICATION_SUCCESS)
            await self.event_manager.publish("HEALTH_WORKOUT_LOG_DELETED", {"id": workout_to_delete.id})
            self.logger.info(message)
            return {"success": True, "output": message, "error": None}
        
        return {"success": False, "output": "Erro desconhecido ao remover registo de exerc√≠cio.", "error": "Unknown error"}


    # --------------------------------------------------------------------- Plugin Interface

    def register_commands(self, executor: CommandExecutor) -> None:
        """Registers health management commands with the CommandExecutor."""
        self.logger.info("A registar comandos do plugin HealthManager...")
        executor.register_command("add_health_metric", self._add_health_metric_command)
        executor.register_command("list_health_metrics", self._list_health_metrics_command)
        executor.register_command("add_medication_reminder", self._add_medication_reminder_command)
        executor.register_command("list_medication_reminders", self._list_medication_reminders_command)
        executor.register_command("toggle_medication_reminder", self._toggle_medication_reminder_command)
        executor.register_command("delete_medication_reminder", self._delete_medication_reminder_command)
        executor.register_command("add_workout_log", self._add_workout_log_command)
        executor.register_command("list_workout_logs", self._list_workout_logs_command)
        executor.register_command("delete_workout_log", self._delete_workout_log_command)
        self.logger.info("Comandos HealthManager registados.")

    def get_tools_schema(self) -> List[Dict[str, Any]]:
        """
        Returns a list of tool definitions (schemas) for health features.
        These schemas are exposed to the LLM for function calling.
        """
        return [
            # --- Health Metrics ---
            {
                "type": "function",
                "function": {
                    "name": "add_health_metric",
                    "description": "Adiciona uma nova m√©trica de sa√∫de ao seu registo (ex: peso, consumo de √°gua, passos). Requer o nome da m√©trica, valor e unidade. Opcionalmente, pode incluir a data/hora e notas.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "O nome da m√©trica de sa√∫de (ex: 'peso', '√°gua', 'passos').",
                            },
                            "value": {
                                "type": "number",
                                "format": "float",
                                "description": "O valor num√©rico da m√©trica.",
                            },
                            "unit": {
                                "type": "string",
                                "description": "A unidade de medida da m√©trica (ex: 'kg', 'litros', 'passos').",
                            },
                            "timestamp": {
                                "type": "string",
                                "description": "A data e hora do registo da m√©trica no formato ISO 8601 (YYYY-MM-DD HH:MM). Padr√£o para a hora atual. Opcional.",
                            },
                            "notes": {
                                "type": "string",
                                "description": "Quaisquer notas adicionais sobre a m√©trica. Opcional.",
                            }
                        },
                        "required": ["name", "value", "unit"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "list_health_metrics",
                    "description": "Lista as m√©tricas de sa√∫de registadas, mostrando os valores mais recentes. Pode filtrar por nome da m√©trica e limitar o n√∫mero de resultados.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "O nome da m√©trica de sa√∫de a listar (ex: 'peso', '√°gua'). Se omitido, lista todas as m√©tricas. Opcional.",
                            },
                            "limit": {
                                "type": "integer",
                                "description": "O n√∫mero m√°ximo de m√©tricas a retornar. Padr√£o para 5.",
                                "default": 5,
                                "minimum": 1
                            }
                        },
                        "required": [],
                    },
                },
            },
            # --- Medication Reminders ---
            {
                "type": "function",
                "function": {
                    "name": "add_medication_reminder",
                    "description": "Adiciona um novo lembrete para tomar uma medica√ß√£o. Requer o nome da medica√ß√£o, dosagem e a hora agendada. A hora deve ser no formato HH:MM.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "medication_name": {
                                "type": "string",
                                "description": "O nome da medica√ß√£o (ex: 'Paracetamol').",
                            },
                            "dosage": {
                                "type": "string",
                                "description": "A dosagem da medica√ß√£o (ex: '500mg', '1 comprimido').",
                            },
                            "schedule_time": {
                                "type": "string",
                                "description": "A hora agendada para o lembrete no formato HH:MM (ex: '09:00', '18:30').",
                                "pattern": "^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$" # Regex para HH:MM
                            },
                            "notes": {
                                "type": "string",
                                "description": "Quaisquer notas adicionais sobre a medica√ß√£o ou o lembrete. Opcional.",
                            },
                            "is_enabled": {
                                "type": "boolean",
                                "description": "Define se o lembrete deve ser ativado imediatamente. Padr√£o para verdadeiro.",
                                "default": True
                            }
                        },
                        "required": ["medication_name", "dosage", "schedule_time"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "list_medication_reminders",
                    "description": "Lista os lembretes de medica√ß√£o definidos, opcionalmente filtrando por status (ativado ou desativado).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "is_enabled": {
                                "type": "boolean",
                                "description": "Define se deve listar apenas lembretes ativados ('true') ou desativados ('false'). Se omitido, lista todos. Opcional.",
                            }
                        },
                        "required": [],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "toggle_medication_reminder",
                    "description": "Ativa ou desativa um lembrete de medica√ß√£o existente. Requer o ID completo ou um prefixo √∫nico do lembrete.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "reminder_id_prefix": {
                                "type": "string",
                                "description": "O ID completo ou um prefixo √∫nico do lembrete de medica√ß√£o a ser ativado/desativado.",
                            },
                            "enable": {
                                "type": "boolean",
                                "description": "Defina para 'true' para ativar o lembrete, 'false' para desativar. Padr√£o para 'true'.",
                                "default": True
                            }
                        },
                        "required": ["reminder_id_prefix", "enable"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "delete_medication_reminder",
                    "description": "Remove um lembrete de medica√ß√£o existente. Requer o ID completo ou um prefixo √∫nico do lembrete. Esta a√ß√£o √© irrevers√≠vel.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "reminder_id_prefix": {
                                "type": "string",
                                "description": "O ID completo ou um prefixo √∫nico do lembrete de medica√ß√£o a ser removido.",
                            },
                        },
                        "required": ["reminder_id_prefix"],
                    },
                },
            },
            # --- Workout Logs ---
            {
                "type": "function",
                "function": {
                    "name": "add_workout_log",
                    "description": "Adiciona um novo registo de exerc√≠cio ou atividade f√≠sica. Requer o tipo de atividade e a dura√ß√£o em minutos. Opcionalmente, pode incluir calorias queimadas, dist√¢ncia percorrida, data/hora e notas.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "activity_type": {
                                "type": "string",
                                "description": "O tipo de atividade f√≠sica (ex: 'corrida', 'muscula√ß√£o', 'yoga').",
                            },
                            "duration_minutes": {
                                "type": "number",
                                "format": "float",
                                "description": "A dura√ß√£o da atividade em minutos.",
                            },
                            "calories_burned": {
                                "type": "number",
                                "format": "float",
                                "description": "O n√∫mero estimado de calorias queimadas. Opcional.",
                            },
                            "distance_km": {
                                "type": "number",
                                "format": "float",
                                "description": "A dist√¢ncia percorrida em quil√≥metros. Opcional.",
                            },
                            "timestamp": {
                                "type": "string",
                                "description": "A data e hora do registo do exerc√≠cio no formato ISO 8601 (YYYY-MM-DD HH:MM). Padr√£o para a hora atual. Opcional.",
                            },
                            "notes": {
                                "type": "string",
                                "description": "Quaisquer notas adicionais sobre o treino. Opcional.",
                            }
                        },
                        "required": ["activity_type", "duration_minutes"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "list_workout_logs",
                    "description": "Lista os registos de exerc√≠cios, mostrando os mais recentes. Pode filtrar por tipo de atividade e limitar o n√∫mero de resultados.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "activity_type": {
                                "type": "string",
                                "description": "O tipo de atividade f√≠sica a listar (ex: 'corrida'). Se omitido, lista todos os registos. Opcional.",
                            },
                            "limit": {
                                "type": "integer",
                                "description": "O n√∫mero m√°ximo de registos a retornar. Padr√£o para 5.",
                                "default": 5,
                                "minimum": 1
                            }
                        },
                        "required": [],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "delete_workout_log",
                    "description": "Remove um registo de exerc√≠cio existente. Requer o ID completo ou um prefixo √∫nico do registo. Esta a√ß√£o √© irrevers√≠vel.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "workout_id_prefix": {
                                "type": "string",
                                "description": "O ID completo ou um prefixo √∫nico do registo de exerc√≠cio a ser removido.",
                            },
                        },
                        "required": ["workout_id_prefix"],
                    },
                },
            },
        ]

    async def _speak_response(self, text: str) -> None:
        """Helper para vocalizar respostas atrav√©s do m√≥dulo TTS principal do GEM."""
        if self.tts_module:
            await self.tts_module.speak(text)
        else:
            self.logger.warning(f"M√≥dulo TTS n√£o dispon√≠vel para falar: '{text}'")

    def shutdown(self) -> None:
        """Stops any background tasks and performs cleanup."""
        self.logger.info("HealthManager a ser desligado. A parar a tarefa de verifica√ß√£o de medica√ß√£o.")
        if self._medication_check_task:
            self._medication_check_task.cancel()
            self._medication_check_task = None
        self.event_manager.unsubscribe("GEM_SHUTDOWN", self._on_gem_shutdown)


# =============================================================================
# CLI Test
# =============================================================================

if __name__ == "__main__":
    import asyncio
    
    # Configure logging for standalone test
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger("TestHealthManager")

    # --- Dummy Implementations for testing ---
    class DummyEventManager:
        def __init__(self, logger_instance):
            self.logger = logger_instance
            self._listeners = defaultdict(list)
        async def publish(self, event_type: str, data: Optional[Dict[str, Any]] = None) -> None:
            self.logger.info(f"Dummy EventManager: Publicado '{event_type}' com {data}")
        def subscribe(self, event_type: str, listener: Callable) -> None:
            self.logger.debug(f"Dummy EventManager: Subscrito '{listener.__name__}' para '{event_type}'")
            self._listeners[event_type].append(listener)
        def unsubscribe(self, event_type: str, listener: Callable) -> None:
            if event_type in self._listeners and listener in self._listeners[event_type]:
                self._listeners[event_type].remove(listener)
                self.logger.debug(f"Dummy EventManager: Desubscrito '{listener.__name__}' de '{event_type}'")

    class DummyNotificationManager:
        def __init__(self, logger_instance):
            self.logger = logger_instance
            self._history: List[Dict[str, Any]] = []
        async def add_notification(self, message: str, level: str = NOTIFICATION_INFO, vocalize: bool = True) -> None:
            self.logger.info(f"Dummy Notification: [{level.upper()}] {message} (Vocalize: {vocalize})")
            self._history.append({"message": message, "level": level})
            await asyncio.sleep(0.01)
        def get_notification_history(self, limit: int = 10) -> List[Dict[str, Any]]:
            return self._history[-limit:]

    class DummyStorage:
        def __init__(self, logger_instance):
            self.logger = logger_instance
            self._data: Dict[str, Any] = defaultdict(list) # Use defaultdict for list storage
        async def get_setting(self, key: str, default: Any = None) -> Any:
            self.logger.info(f"Dummy Storage: A obter '{key}'")
            return self._data.get(key, default)
        async def set_setting(self, key: str, value: Any) -> bool:
            self.logger.info(f"Dummy Storage: A salvar '{key}'")
            self._data[key] = value
            return True

    class DummyTTSModule:
        def __init__(self, logger_instance):
            self.logger = logger_instance
        async def speak(self, text: str) -> None:
            self.logger.info(f"Dummy TTS: A falar: '{text}'")
            await asyncio.sleep(0.01)

    class DummyCommandExecutor:
        def __init__(self, logger_instance):
            self.logger = logger_instance
            self.commands = {}
        def register_command(self, name: str, func: Callable[..., Awaitable[Dict[str, Any]]], **kwargs) -> None:
            self.commands[name] = (func, kwargs)
            self.logger.info(f"Dummy CommandExecutor: Registou comando '{name}'.")
        async def execute(self, command_name: str, *args, **kwargs) -> Dict[str, Any]:
            self.logger.info(f"Dummy CommandExecutor: A executar '{command_name}' com args={args}, kwargs={kwargs}")
            if command_name in self.commands:
                func, default_kwargs = self.commands[command_name]
                merged_kwargs = {**default_kwargs, **kwargs}
                return await func(*args, **merged_kwargs)
            return {"success": False, "output": "", "error": "Comando desconhecido simulado."}

    class DummyConfigManager:
        def __init__(self):
            self.config = type('GEMConfig', (), {
                'general': type('GeneralConfig', (), {
                    'enable_audio_notifications': True
                })()
            })()
        def get_config(self) -> Any:
            return self.config

    class DummyGEM:
        def __init__(self, logger_instance: logging.Logger):
            self.logger = logger_instance
            self.event_manager = DummyEventManager(logger_instance)
            self.notification_manager = DummyNotificationManager(logger_instance)
            self.tts_module = DummyTTSModule(logger_instance)
            self.config_manager = DummyConfigManager()
            self.command_executor = DummyCommandExecutor(logger_instance)
            self.storage = DummyStorage(logger_instance)

    async def run_health_manager_tests():
        print("\n--- Iniciando Testes do HealthManager ---")

        dummy_gem = DummyGEM(logger)
        health_manager = HealthManager(dummy_gem, logger)
        
        health_manager.register_commands(dummy_gem.command_executor)

        await health_manager.initialize()
        await asyncio.sleep(0.1) # Give background task a moment to start

        now = datetime.now()
        
        # --- Teste 1: Adicionar M√©trica de Sa√∫de (Peso) ---
        print("\n--- Teste 1: Adicionar M√©trica de Sa√∫de (Peso) ---")
        result_add_weight = await dummy_gem.command_executor.execute(
            "add_health_metric", name="peso", value=75.5, unit="kg", notes="Depois do almo√ßo"
        )
        print(result_add_weight["output"])
        assert result_add_weight["success"] is True
        assert "M√©trica 'peso' (75.5 kg) registada com sucesso." in result_add_weight["output"]

        result_add_water = await dummy_gem.command_executor.execute(
            "add_health_metric", name="√°gua", value=0.5, unit="litros",
            timestamp=(now - timedelta(hours=1)).isoformat()
        )
        assert result_add_water["success"] is True

        # --- Teste 2: Listar M√©tricas de Sa√∫de ---
        print("\n--- Teste 2: Listar M√©tricas de Sa√∫de ---")
        result_list_metrics = await dummy_gem.command_executor.execute("list_health_metrics", name="peso")
        print(result_list_metrics["output"])
        assert result_list_metrics["success"] is True
        assert "Peso: 75.5 kg" in result_list_metrics["output"]
        
        result_list_all_metrics = await dummy_gem.command_executor.execute("list_health_metrics")
        print(result_list_all_metrics["output"])
        assert "√Ågua: 0.5 litros" in result_list_all_metrics["output"]

        # --- Teste 3: Adicionar Lembrete de Medica√ß√£o ---
        print("\n--- Teste 3: Adicionar Lembrete de Medica√ß√£o ---")
        schedule_time_med = (now + timedelta(minutes=1)).strftime("%H:%M") # Para testar o acionamento
        result_add_medication = await dummy_gem.command_executor.execute(
            "add_medication_reminder",
            medication_name="Vitamina C",
            dosage="1 comprimido",
            schedule_time=schedule_time_med,
            notes="Depois do pequeno-almo√ßo"
        )
        print(result_add_medication["output"])
        assert result_add_medication["success"] is True
        assert f"Lembrete para 'Vitamina C' (1 comprimido) agendado para {schedule_time_med}." in result_add_medication["output"]

        # --- Teste 4: Aguardar Lembrete de Medica√ß√£o ---
        print(f"\n--- Teste 4: Aguardar 65 segundos para Lembrete de Medica√ß√£o (Hor√°rio: {schedule_time_med}) ---")
        await asyncio.sleep(65) # Esperar o lembrete ser acionado
        assert any(f"Lembrete de medica√ß√£o: √â hora de tomar 1 comprimido de Vitamina C." in n["message"] for n in dummy_gem.notification_manager.get_notification_history())
        
        # --- Teste 5: Listar Lembretes de Medica√ß√£o ---
        print("\n--- Teste 5: Listar Lembretes de Medica√ß√£o ---")
        result_list_medication = await dummy_gem.command_executor.execute("list_medication_reminders")
        print(result_list_medication["output"])
        assert result_list_medication["success"] is True
        assert "Vitamina C (1 comprimido)" in result_list_medication["output"]

        # --- Teste 6: Desativar e Ativar Lembrete de Medica√ß√£o ---
        print("\n--- Teste 6: Desativar e Ativar Lembrete de Medica√ß√£o ---")
        med_id_to_toggle = next(r.id for r in health_manager._medication_reminders.values() if r.medication_name == "Vitamina C")
        result_disable_med = await dummy_gem.command_executor.execute("toggle_medication_reminder", reminder_id_prefix=med_id_to_toggle[:8], enable=False)
        print(result_disable_med["output"])
        assert result_disable_med["success"] is True
        assert "Lembrete para 'Vitamina C' desativado com sucesso." in result_disable_med["output"]
        assert not health_manager._medication_reminders[med_id_to_toggle].is_enabled

        result_enable_med = await dummy_gem.command_executor.execute("toggle_medication_reminder", reminder_id_prefix=med_id_to_toggle[:8], enable=True)
        print(result_enable_med["output"])
        assert result_enable_med["success"] is True
        assert "Lembrete para 'Vitamina C' ativado com sucesso." in result_enable_med["output"]
        assert health_manager._medication_reminders[med_id_to_toggle].is_enabled

        # --- Teste 7: Adicionar Registo de Exerc√≠cio ---
        print("\n--- Teste 7: Adicionar Registo de Exerc√≠cio ---")
        result_add_workout = await dummy_gem.command_executor.execute(
            "add_workout_log", activity_type="Corrida", duration_minutes=30.0, calories_burned=350.0, distance_km=5.0
        )
        print(result_add_workout["output"])
        assert result_add_workout["success"] is True
        assert "Registo de exerc√≠cio 'Corrida' (30.0 minutos) adicionado com sucesso." in result_add_workout["output"]

        # --- Teste 8: Listar Registos de Exerc√≠cios ---
        print("\n--- Teste 8: Listar Registos de Exerc√≠cios ---")
        result_list_workouts = await dummy_gem.command_executor.execute("list_workout_logs", activity_type="Corrida")
        print(result_list_workouts["output"])
        assert result_list_workouts["success"] is True
        assert "Corrida - Dura√ß√£o: 30 min, Queimou: 350 cal, Dist√¢ncia: 5.00 km" in result_list_workouts["output"]

        # --- Teste 9: Remover Lembrete de Medica√ß√£o ---
        print("\n--- Teste 9: Remover Lembrete de Medica√ß√£o ---")
        med_id_to_delete = next(r.id for r in health_manager._medication_reminders.values() if r.medication_name == "Vitamina C")
        result_delete_med = await dummy_gem.command_executor.execute("delete_medication_reminder", reminder_id_prefix=med_id_to_delete[:8])
        print(result_delete_med["output"])
        assert result_delete_med["success"] is True
        assert "Lembrete para 'Vitamina C' (ID:" in result_delete_med["output"] and "removido." in result_delete_med["output"]
        assert med_id_to_delete not in health_manager._medication_reminders

        # --- Teste 10: Remover Registo de Exerc√≠cio ---
        print("\n--- Teste 10: Remover Registo de Exerc√≠cio ---")
        workout_id_to_delete = next(w.id for w in health_manager._workout_logs.values() if w.activity_type == "Corrida")
        result_delete_workout = await dummy_gem.command_executor.execute("delete_workout_log", workout_id_prefix=workout_id_to_delete[:8])
        print(result_delete_workout["output"])
        assert result_delete_workout["success"] is True
        assert "Registo de exerc√≠cio 'Corrida' (ID:" in result_delete_workout["output"] and "removido." in result_delete_workout["output"]
        assert workout_id_to_delete not in health_manager._workout_logs

        print("\n--- Testes do HealthManager conclu√≠dos com sucesso. ---")
        health_manager.shutdown()
        await asyncio.sleep(0.1) # Give shutdown task a moment
        assert health_manager._medication_check_task is None or health_manager._medication_check_task.done()

    asyncio.run(run_health_manager_tests())

