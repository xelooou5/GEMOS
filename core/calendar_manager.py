#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
üíé GEM OS - Calendar Manager (core/calendar_manager.py)
Manages user calendar events, including creation, listing, and updates.

Responsibilities
----------------
- Create, retrieve, update, and delete calendar events.
- Persist events using the Storage module.
- Integrate with NotificationManager for event alerts.
- Expose calendar capabilities as tools for the LLM.
- Publish calendar-related events.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable, Awaitable

from core.plugins import BasePlugin, CommandExecutor, GEMVoiceAssistant
from core.notification_manager import NotificationManager, NOTIFICATION_INFO, NOTIFICATION_WARNING, NOTIFICATION_SUCCESS

# Forward declarations for type hinting
class EventManager:
    async def publish(self, event_type: str, data: Optional[Dict[str, Any]] = None) -> None:
        pass

class Storage:
    async def get_setting(self, key: str, default: Any = None) -> Any:
        pass
    async def set_setting(self, key: str, value: Any) -> bool:
        pass

class TTSModule:
    async def speak(self, text: str) -> None:
        pass

# --- Dataclass para Evento de Calend√°rio ---
@dataclass
class CalendarEvent:
    id: str
    title: str
    start_time: datetime
    end_time: datetime
    description: Optional[str] = None
    location: Optional[str] = None
    reminders: List[datetime] = field(default_factory=list) # List of reminder datetimes

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "description": self.description,
            "location": self.location,
            "reminders": [r.isoformat() for r in self.reminders],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CalendarEvent:
        return cls(
            id=data["id"],
            title=data["title"],
            start_time=datetime.fromisoformat(data["start_time"]),
            end_time=datetime.fromisoformat(data["end_time"]),
            description=data.get("description"),
            location=data.get("location"),
            reminders=[datetime.fromisoformat(r) for r in data.get("reminders", [])],
        )

# --- Calendar Manager como um Plugin ---
class CalendarManager(BasePlugin):
    """
    Manages user calendar events for GEM OS, acting as a plugin.
    """
    STORAGE_KEY = "user_calendar_events"

    def __init__(self, gem_instance: GEMVoiceAssistant, logger: Optional[logging.Logger] = None):
        super().__init__(gem_instance, logger)
        self.logger.info("CalendarManager plugin inicializado.")
        
        self.event_manager: EventManager = gem_instance.event_manager
        self.notification_manager: NotificationManager = gem_instance.notification_manager
        self.storage: Storage = gem_instance.storage
        self.tts_module: TTSModule = gem_instance.tts_module

        self._events: Dict[str, CalendarEvent] = {} # {event_id: CalendarEvent_object}
        self._events_loaded = asyncio.Event() # Evento para sinalizar que os eventos foram carregados
        self._check_task: Optional[asyncio.Task] = None
        self._check_interval_seconds: int = 60 # Check every minute for upcoming events

    async def initialize(self) -> None:
        """Loads events from storage and starts the background event checker."""
        await self._load_events_from_storage()
        if not self._check_task:
            self._check_task = asyncio.create_task(self._periodic_event_check())
            self.logger.info("Verifica√ß√£o peri√≥dica de eventos de calend√°rio iniciada.")
        self.event_manager.subscribe("GEM_SHUTDOWN", self._on_gem_shutdown)
        self.logger.info("CalendarManager inicializado.")

    async def _on_gem_shutdown(self, event_data: Dict[str, Any]) -> None:
        """Handler for GEM_SHUTDOWN event to gracefully stop event checks."""
        self.logger.info("Recebido GEM_SHUTDOWN. A parar as verifica√ß√µes de eventos de calend√°rio.")
        self.shutdown()

    async def _load_events_from_storage(self) -> None:
        """Loads calendar events from persistent storage."""
        try:
            events_data = await self.storage.get_setting(self.STORAGE_KEY, [])
            for event_dict in events_data:
                try:
                    event = CalendarEvent.from_dict(event_dict)
                    self._events[event.id] = event
                except Exception as e:
                    self.logger.error(f"Erro ao carregar evento do armazenamento: {e} - Dados: {event_dict}", exc_info=True)
            self.logger.info(f"Carregados {len(self._events)} eventos do calend√°rio do armazenamento.")
        except Exception as e:
            self.logger.error(f"Falha ao carregar eventos do calend√°rio do armazenamento: {e}", exc_info=True)
        finally:
            self._events_loaded.set() # Sinaliza que os eventos foram carregados

    async def _save_events_to_storage(self) -> None:
        """Saves current calendar events to persistent storage."""
        try:
            events_data = [event.to_dict() for event in self._events.values()]
            await self.storage.set_setting(self.STORAGE_KEY, events_data)
            self.logger.debug(f"Salvos {len(self._events)} eventos para o armazenamento.")
        except Exception as e:
            self.logger.error(f"Falha ao salvar eventos no armazenamento: {e}", exc_info=True)

    async def _periodic_event_check(self) -> None:
        """Periodically checks for upcoming event reminders."""
        self.logger.debug("Loop de verifica√ß√£o peri√≥dica de eventos de calend√°rio iniciado.")
        await self._events_loaded.wait() # Wait until events are loaded
        while True:
            try:
                await self._check_upcoming_events()
                await asyncio.sleep(self._check_interval_seconds)
            except asyncio.CancelledError:
                self.logger.info("Tarefa de verifica√ß√£o peri√≥dica de eventos de calend√°rio cancelada.")
                break
            except Exception as e:
                self.logger.error(f"Erro no loop de verifica√ß√£o de eventos de calend√°rio: {e}", exc_info=True)
                await asyncio.sleep(self._check_interval_seconds * 2) # Wait longer on error

    async def _check_upcoming_events(self) -> None:
        """Checks for events that are due for a reminder or about to start."""
        now = datetime.now()
        for event_id, event in list(self._events.items()):
            # Check for general start time alert (e.g., 5 minutes before)
            if event.start_time > now and (event.start_time - now) < timedelta(minutes=5) and \
               not any("start_alert" in r for r in event.reminders): # Prevent duplicate alerts
                self.logger.info(f"Evento '{event.title}' a come√ßar em breve: {event.start_time.strftime('%H:%M')}.")
                message = f"Lembrete: O evento '{event.title}' come√ßa em breve, √†s {event.start_time.strftime('%H:%M')}."
                await self.notification_manager.add_notification(message, level=NOTIFICATION_WARNING, vocalize=True)
                await self.tts_module.speak(message)
                event.reminders.append("start_alert") # Mark as alerted for start time
                await self._save_events_to_storage()
                await self.event_manager.publish("CALENDAR_EVENT_UPCOMING", event.to_dict())
            
            # Check specific reminders
            for reminder_time in event.reminders:
                if isinstance(reminder_time, datetime) and reminder_time <= now and \
                   (now - reminder_time) < timedelta(minutes=1): # Trigger if within 1 minute of now
                    self.logger.info(f"Lembrete de evento '{event.title}' disparado.")
                    message = f"Lembrete: '{event.title}' est√° a acontecer agora!"
                    await self.notification_manager.add_notification(message, level=NOTIFICATION_INFO, vocalize=True)
                    await self.tts_module.speak(message)
                    # Remove this specific reminder or mark as triggered if recurring/multiple
                    event.reminders = [r for r in event.reminders if r != reminder_time] # Remove once triggered
                    await self._save_events_to_storage()
                    await self.event_manager.publish("CALENDAR_REMINDER_TRIGGERED", event.to_dict())


    # --------------------------------------------------------------------- Commands

    async def _create_calendar_event_command(self, title: str, start_time: str, end_time: str,
                                            description: Optional[str] = None, location: Optional[str] = None,
                                            reminders: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Cria um novo evento de calend√°rio.
        start_time e end_time devem ser strings no formato ISO 8601 (YYYY-MM-DD HH:MM).
        reminders √© uma lista de strings de data/hora no mesmo formato.
        """
        await self._events_loaded.wait() # Ensure events are loaded

        try:
            parsed_start_time = datetime.fromisoformat(start_time)
            parsed_end_time = datetime.fromisoformat(end_time)
        except ValueError:
            await self._speak_response("Formato de data/hora inv√°lido. Por favor, use 'AAAA-MM-DD HH:MM'.")
            return {"success": False, "output": "Formato de data/hora inv√°lido.", "error": "Invalid date/time format"}

        if parsed_start_time >= parsed_end_time:
            await self._speak_response("A hora de in√≠cio deve ser anterior √† hora de t√©rmino.")
            return {"success": False, "output": "Erro de data/hora.", "error": "Start time must be before end time"}

        parsed_reminders = []
        if reminders:
            for r_str in reminders:
                try:
                    parsed_reminders.append(datetime.fromisoformat(r_str))
                except ValueError:
                    await self._speak_response(f"Formato de lembrete inv√°lido: '{r_str}'. Ignorando este lembrete.")
                    self.logger.warning(f"Formato de lembrete inv√°lido: '{r_str}'. Ignorando.")

        event_id = str(uuid.uuid4())
        new_event = CalendarEvent(
            id=event_id,
            title=title,
            start_time=parsed_start_time,
            end_time=parsed_end_time,
            description=description,
            location=location,
            reminders=parsed_reminders
        )
        self._events[event_id] = new_event
        await self._save_events_to_storage()
        
        message = f"Evento '{title}' criado para {new_event.start_time.strftime('%Y-%m-%d %H:%M')}."
        await self._speak_response(message)
        await self.notification_manager.add_notification(message, level=NOTIFICATION_SUCCESS)
        await self.event_manager.publish("CALENDAR_EVENT_CREATED", new_event.to_dict())
        self.logger.info(message)
        return {"success": True, "output": message, "error": None}

    async def _list_calendar_events_command(self, period: str = "today") -> Dict[str, Any]:
        """
        Lista eventos do calend√°rio para um determinado per√≠odo.
        Per√≠odos suportados: "today", "tomorrow", "this_week", "next_7_days", "all".
        """
        await self._events_loaded.wait() # Ensure events are loaded

        now = datetime.now()
        filtered_events = []

        for event in self._events.values():
            if period == "all":
                filtered_events.append(event)
            elif period == "today" and event.start_time.date() == now.date():
                filtered_events.append(event)
            elif period == "tomorrow" and event.start_time.date() == (now + timedelta(days=1)).date():
                filtered_events.append(event)
            elif period == "this_week" and now.isocalendar()[1] == event.start_time.isocalendar()[1] and now.year == event.start_time.year:
                filtered_events.append(event)
            elif period == "next_7_days" and now.date() <= event.start_time.date() <= (now + timedelta(days=7)).date():
                filtered_events.append(event)
        
        filtered_events.sort(key=lambda e: e.start_time) # Sort by start time

        if not filtered_events:
            message = f"N√£o h√° eventos para o per√≠odo '{period}'."
            await self._speak_response(message)
            return {"success": True, "output": message, "error": None}

        output_lines = [f"Eventos para {period}:"]
        for i, event in enumerate(filtered_events):
            output_lines.append(f"{i+1}. {event.title} (In√≠cio: {event.start_time.strftime('%Y-%m-%d %H:%M')}, Fim: {event.end_time.strftime('%H:%M')})")
            if event.location:
                output_lines.append(f"   Local: {event.location}")
            if event.description:
                output_lines.append(f"   Descri√ß√£o: {event.description}")
            output_lines.append(f"   (ID: {event.id[:8]}...)")
            output_lines.append("-" * 20)
        
        message = "\n".join(output_lines)
        await self._speak_response(f"Os eventos para {period} foram listados. Verifique o ecr√£ para os detalhes.")
        return {"success": True, "output": message, "error": None}

    async def _update_calendar_event_command(self, event_id_prefix: str, new_title: Optional[str] = None,
                                            new_start_time: Optional[str] = None, new_end_time: Optional[str] = None,
                                            new_description: Optional[str] = None, new_location: Optional[str] = None,
                                            new_reminders: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Atualiza um evento de calend√°rio existente.
        Requer um prefixo do ID do evento.
        """
        await self._events_loaded.wait() # Ensure events are loaded

        event_to_update: Optional[CalendarEvent] = None
        matching_events = [e for e in self._events.values() if e.id.startswith(event_id_prefix)]

        if len(matching_events) == 1:
            event_to_update = matching_events[0]
        elif len(matching_events) > 1:
            message = f"M√∫ltiplos eventos correspondem ao ID '{event_id_prefix}'. Por favor, seja mais espec√≠fico."
            await self._speak_response(message)
            return {"success": False, "output": message, "error": "Multiple matches"}
        else:
            message = f"Nenhum evento encontrado com o ID '{event_id_prefix}'."
            await self._speak_response(message)
            return {"success": False, "output": message, "error": "Event not found"}

        if event_to_update:
            if new_title: event_to_update.title = new_title
            if new_description: event_to_update.description = new_description
            if new_location: event_to_update.location = new_location

            try:
                if new_start_time: event_to_update.start_time = datetime.fromisoformat(new_start_time)
                if new_end_time: event_to_update.end_time = datetime.fromisoformat(new_end_time)
            except ValueError:
                await self._speak_response("Formato de data/hora inv√°lido para atualiza√ß√£o. Por favor, use 'AAAA-MM-DD HH:MM'.")
                return {"success": False, "output": "Formato de data/hora inv√°lido.", "error": "Invalid date/time format"}

            if event_to_update.start_time >= event_to_update.end_time:
                await self._speak_response("A hora de in√≠cio atualizada deve ser anterior √† hora de t√©rmino.")
                return {"success": False, "output": "Erro de data/hora.", "error": "Updated start time must be before end time"}

            if new_reminders is not None: # Can be empty list to clear
                parsed_new_reminders = []
                for r_str in new_reminders:
                    try:
                        parsed_new_reminders.append(datetime.fromisoformat(r_str))
                    except ValueError:
                        await self._speak_response(f"Formato de lembrete inv√°lido: '{r_str}'. Ignorando este lembrete.")
                        self.logger.warning(f"Formato de lembrete inv√°lido: '{r_str}'. Ignorando.")
                event_to_update.reminders = parsed_new_reminders
            
            await self._save_events_to_storage()
            message = f"Evento '{event_to_update.title}' (ID: {event_to_update.id[:8]}...) atualizado com sucesso."
            await self._speak_response(message)
            await self.notification_manager.add_notification(message, level=NOTIFICATION_INFO)
            await self.event_manager.publish("CALENDAR_EVENT_UPDATED", event_to_update.to_dict())
            self.logger.info(message)
            return {"success": True, "output": message, "error": None}
        
        return {"success": False, "output": "Erro desconhecido ao atualizar evento.", "error": "Unknown error"}

    async def _delete_calendar_event_command(self, event_id_prefix: str) -> Dict[str, Any]:
        """
        Remove um evento de calend√°rio usando um prefixo do ID.
        """
        await self._events_loaded.wait() # Ensure events are loaded

        event_to_delete: Optional[CalendarEvent] = None
        matching_events = [e for e in self._events.values() if e.id.startswith(event_id_prefix)]

        if len(matching_events) == 1:
            event_to_delete = matching_events[0]
        elif len(matching_events) > 1:
            message = f"M√∫ltiplos eventos correspondem ao ID '{event_id_prefix}'. Por favor, seja mais espec√≠fico."
            await self._speak_response(message)
            return {"success": False, "output": message, "error": "Multiple matches"}
        else:
            message = f"Nenhum evento encontrado com o ID '{event_id_prefix}'."
            await self._speak_response(message)
            return {"success": False, "output": message, "error": "Event not found"}

        if event_to_delete:
            del self._events[event_to_delete.id]
            await self._save_events_to_storage()
            message = f"Evento '{event_to_delete.title}' (ID: {event_to_delete.id[:8]}...) removido."
            await self._speak_response(message)
            await self.notification_manager.add_notification(message, level=NOTIFICATION_INFO)
            await self.event_manager.publish("CALENDAR_EVENT_DELETED", {"event_id": event_to_delete.id})
            self.logger.info(message)
            return {"success": True, "output": message, "error": None}
        
        return {"success": False, "output": "Erro desconhecido ao remover evento.", "error": "Unknown error"}


    # --------------------------------------------------------------------- Plugin Interface

    def register_commands(self, executor: CommandExecutor) -> None:
        """Registers calendar management commands with the CommandExecutor."""
        self.logger.info("A registar comandos do plugin CalendarManager...")
        executor.register_command("create_calendar_event", self._create_calendar_event_command)
        executor.register_command("list_calendar_events", self._list_calendar_events_command)
        executor.register_command("update_calendar_event", self._update_calendar_event_command)
        executor.register_command("delete_calendar_event", self._delete_calendar_event_command)
        self.logger.info("Comandos CalendarManager registados.")

    def get_tools_schema(self) -> List[Dict[str, Any]]:
        """
        Returns a list of tool definitions (schemas) for calendar features.
        These schemas are exposed to the LLM for function calling.
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": "create_calendar_event",
                    "description": "Cria um novo evento de calend√°rio com um t√≠tulo, hora de in√≠cio e hora de t√©rmino. Opcionalmente pode incluir uma descri√ß√£o, localiza√ß√£o e lembretes.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {
                                "type": "string",
                                "description": "O t√≠tulo do evento.",
                            },
                            "start_time": {
                                "type": "string",
                                "description": "A data e hora de in√≠cio do evento no formato ISO 8601 (YYYY-MM-DD HH:MM).",
                            },
                            "end_time": {
                                "type": "string",
                                "description": "A data e hora de t√©rmino do evento no formato ISO 8601 (YYYY-MM-DD HH:MM).",
                            },
                            "description": {
                                "type": "string",
                                "description": "Uma descri√ß√£o detalhada do evento. Opcional.",
                            },
                            "location": {
                                "type": "string",
                                "description": "A localiza√ß√£o do evento. Opcional.",
                            },
                            "reminders": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Uma lista de datas/horas no formato ISO 8601 (YYYY-MM-DD HH:MM) para lembretes espec√≠ficos. Opcional.",
                            }
                        },
                        "required": ["title", "start_time", "end_time"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "list_calendar_events",
                    "description": "Lista os eventos de calend√°rio para um per√≠odo espec√≠fico. Pode listar eventos para 'today' (hoje), 'tomorrow' (amanh√£), 'this_week' (esta semana), 'next_7_days' (pr√≥ximos 7 dias) ou 'all' (todos).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "period": {
                                "type": "string",
                                "description": "O per√≠odo para o qual listar os eventos. Padr√£o para 'today'.",
                                "enum": ["today", "tomorrow", "this_week", "next_7_days", "all"],
                                "default": "today"
                            }
                        },
                        "required": [],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "update_calendar_event",
                    "description": "Atualiza os detalhes de um evento de calend√°rio existente. Requer o ID completo ou um prefixo √∫nico do evento. Pode atualizar o t√≠tulo, hor√°rios, descri√ß√£o, localiza√ß√£o e lembretes.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "event_id_prefix": {
                                "type": "string",
                                "description": "O ID completo ou um prefixo √∫nico do evento a ser atualizado.",
                            },
                            "new_title": {
                                "type": "string",
                                "description": "Um novo t√≠tulo para o evento. Opcional.",
                            },
                            "new_start_time": {
                                "type": "string",
                                "description": "Uma nova data e hora de in√≠cio no formato ISO 8601 (YYYY-MM-DD HH:MM). Opcional.",
                            },
                            "new_end_time": {
                                "type": "string",
                                "description": "Uma nova data e hora de t√©rmino no formato ISO 8601 (YYYY-MM-DD HH:MM). Opcional.",
                            },
                            "new_description": {
                                "type": "string",
                                "description": "Uma nova descri√ß√£o para o evento. Opcional.",
                            },
                            "new_location": {
                                "type": "string",
                                "description": "Uma nova localiza√ß√£o para o evento. Opcional.",
                            },
                            "new_reminders": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Uma nova lista de datas/horas para lembretes no formato ISO 8601 (YYYY-MM-DD HH:MM). Opcional. Se fornecido, substituir√° os lembretes existentes.",
                            }
                        },
                        "required": ["event_id_prefix"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "delete_calendar_event",
                    "description": "Remove um evento de calend√°rio existente. Requer o ID completo ou um prefixo √∫nico do evento.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "event_id_prefix": {
                                "type": "string",
                                "description": "O ID completo ou um prefixo √∫nico do evento a ser removido.",
                            }
                        },
                        "required": ["event_id_prefix"],
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
        self.logger.info("CalendarManager a ser desligado. A parar a tarefa de verifica√ß√£o de eventos.")
        if self._check_task:
            self._check_task.cancel()
            self._check_task = None
        self.event_manager.unsubscribe("GEM_SHUTDOWN", self._on_gem_shutdown)


# =============================================================================
# CLI Test
# =============================================================================

if __name__ == "__main__":
    import asyncio
    
    # Configure logging for standalone test
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger("TestCalendarManager")

    # --- Dummy Implementations for testing ---
    class DummyEventManager:
        def __init__(self, logger_instance):
            self.logger = logger_instance
        async def publish(self, event_type: str, data: Optional[Dict[str, Any]] = None) -> None:
            self.logger.info(f"Dummy EventManager: Publicado '{event_type}' com {data}")

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
            self._data: Dict[str, Any] = {}
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
                    'enable_audio_notifications': True # Para notificar
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

    async def run_calendar_manager_tests():
        print("\n--- Iniciando Testes do CalendarManager ---")

        dummy_gem = DummyGEM(logger)
        calendar_manager = CalendarManager(dummy_gem, logger)
        
        calendar_manager.register_commands(dummy_gem.command_executor)

        await calendar_manager.initialize()

        now = datetime.now()
        tomorrow = now + timedelta(days=1)
        next_week = now + timedelta(days=7)

        print("\n--- Teste 1: Criar Evento ---")
        event1_start = (now + timedelta(minutes=1)).replace(second=0, microsecond=0)
        event1_end = (now + timedelta(minutes=3)).replace(second=0, microsecond=0)
        result_create1 = await dummy_gem.command_executor.execute(
            "create_calendar_event",
            title="Reuni√£o de Equipa",
            start_time=event1_start.isoformat(),
            end_time=event1_end.isoformat(),
            description="Discuss√£o do projeto X",
            location="Sala de Reuni√µes",
            reminders=[(event1_start - timedelta(seconds=5)).isoformat()] # 5s antes para teste
        )
        print(result_create1["output"])
        assert result_create1["success"] is True
        assert "Evento 'Reuni√£o de Equipa' criado" in result_create1["output"]

        event2_start = (tomorrow + timedelta(hours=10)).replace(second=0, microsecond=0)
        event2_end = (tomorrow + timedelta(hours=11)).replace(second=0, microsecond=0)
        result_create2 = await dummy_gem.command_executor.execute(
            "create_calendar_event",
            title="Consulta M√©dica",
            start_time=event2_start.isoformat(),
            end_time=event2_end.isoformat(),
            location="Cl√≠nica Central"
        )
        print(result_create2["output"])
        assert result_create2["success"] is True

        print("\n--- Teste 2: Listar Eventos de Hoje ---")
        result_list_today = await dummy_gem.command_executor.execute("list_calendar_events", period="today")
        print(result_list_today["output"])
        assert "Reuni√£o de Equipa" in result_list_today["output"]
        assert "Nenhum evento para o per√≠odo 'today'." not in result_list_today["output"]

        print("\n--- Teste 3: Listar Eventos de Amanh√£ ---")
        result_list_tomorrow = await dummy_gem.command_executor.execute("list_calendar_events", period="tomorrow")
        print(result_list_tomorrow["output"])
        assert "Consulta M√©dica" in result_list_tomorrow["output"]

        print("\n--- Teste 4: Verificar lembrete de evento (aguardando 5 segundos) ---")
        print("Aguardando 5 segundos para o lembrete da 'Reuni√£o de Equipa'...")
        await asyncio.sleep(6) # Aguarda o lembrete (configurado para 5s antes do in√≠cio do evento)

        notification_history = dummy_gem.notification_manager.get_notification_history(limit=10)
        assert any("Lembrete: 'Reuni√£o de Equipa' est√° a acontecer agora!" in n["message"] for n in notification_history)
        print("‚úÖ Lembrete 'Reuni√£o de Equipa' verificado no hist√≥rico de notifica√ß√µes.")

        print("\n--- Teste 5: Atualizar Evento ---")
        event_id_to_update = next(e.id for e in calendar_manager._events.values() if e.title == "Reuni√£o de Equipa")
        new_start_time_update = (now + timedelta(minutes=10)).replace(second=0, microsecond=0).isoformat()
        new_end_time_update = (now + timedelta(minutes=20)).replace(second=0, microsecond=0).isoformat()
        result_update = await dummy_gem.command_executor.execute(
            "update_calendar_event",
            event_id_prefix=event_id_to_update[:8],
            new_title="Reuni√£o de Projeto",
            new_start_time=new_start_time_update,
            new_end_time=new_end_time_update,
            new_location="Online"
        )
        print(result_update["output"])
        assert result_update["success"] is True
        assert "Evento 'Reuni√£o de Projeto' (ID:" in result_update["output"] and "atualizado com sucesso." in result_update["output"]
        
        # Verify update
        updated_event = calendar_manager._events[event_id_to_update]
        assert updated_event.title == "Reuni√£o de Projeto"
        assert updated_event.location == "Online"
        assert updated_event.start_time.isoformat() == new_start_time_update

        print("\n--- Teste 6: Listar Todos os Eventos ---")
        result_list_all = await dummy_gem.command_executor.execute("list_calendar_events", period="all")
        print(result_list_all["output"])
        assert "Reuni√£o de Projeto" in result_list_all["output"]
        assert "Consulta M√©dica" in result_list_all["output"]

        print("\n--- Teste 7: Remover Evento ---")
        event_id_to_delete = next(e.id for e in calendar_manager._events.values() if e.title == "Consulta M√©dica")
        result_delete = await dummy_gem.command_executor.execute("delete_calendar_event", event_id_prefix=event_id_to_delete[:8])
        print(result_delete["output"])
        assert result_delete["success"] is True
        assert "Evento 'Consulta M√©dica' (ID:" in result_delete["output"] and "removido." in result_delete["output"]
        
        # Verify deletion
        assert event_id_to_delete not in calendar_manager._events

        print("\n--- Testes do CalendarManager conclu√≠dos com sucesso. ---")
        calendar_manager.shutdown()
        await asyncio.sleep(0.1) # Give shutdown task a moment
        assert calendar_manager._check_task is None or calendar_manager._check_task.done()

    asyncio.run(run_calendar_manager_tests())

