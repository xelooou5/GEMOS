#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
üíé GEM OS - To-Do Manager (core/todo_manager.py)
Manages user's to-do list and tasks, including creation, listing, updating, and completion.

Responsibilities
----------------
- Create, retrieve, update, and delete to-do tasks.
- Persist tasks using the Storage module.
- Integrate with NotificationManager for task reminders and alerts.
- Expose to-do list capabilities as tools for the LLM.
- Publish task-related events.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
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

# --- Dataclass para Tarefa de Afazeres ---
@dataclass
class TodoTask:
    id: str
    description: str
    due_date: Optional[datetime] = None
    priority: int = 0 # 0=Low, 1=Medium, 2=High
    is_completed: bool = False
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "priority": self.priority,
            "is_completed": self.is_completed,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TodoTask:
        return cls(
            id=data["id"],
            description=data["description"],
            due_date=datetime.fromisoformat(data["due_date"]) if data.get("due_date") else None,
            priority=data.get("priority", 0),
            is_completed=data.get("is_completed", False),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
        )

# --- To-Do Manager como um Plugin ---
class TodoManager(BasePlugin):
    """
    Manages user's to-do tasks for GEM OS, acting as a plugin.
    """
    STORAGE_KEY = "user_todo_tasks"

    def __init__(self, gem_instance: GEMVoiceAssistant, logger: Optional[logging.Logger] = None):
        super().__init__(gem_instance, logger)
        self.logger.info("TodoManager plugin inicializado.")
        
        self.event_manager: EventManager = gem_instance.event_manager
        self.notification_manager: NotificationManager = gem_instance.notification_manager
        self.storage: Storage = gem_instance.storage
        self.tts_module: TTSModule = gem_instance.tts_module

        self._tasks: Dict[str, TodoTask] = {} # {task_id: TodoTask_object}
        self._tasks_loaded = asyncio.Event()
        self._check_task: Optional[asyncio.Task] = None
        self._check_interval_seconds: int = 300 # Check every 5 minutes for upcoming deadlines

    async def initialize(self) -> None:
        """Loads tasks from storage and starts the background task checker."""
        await self._load_tasks_from_storage()
        if not self._check_task:
            self._check_task = asyncio.create_task(self._periodic_task_check())
            self.logger.info("Verifica√ß√£o peri√≥dica de tarefas iniciada.")
        self.event_manager.subscribe("GEM_SHUTDOWN", self._on_gem_shutdown)
        self.logger.info("TodoManager inicializado.")

    async def _on_gem_shutdown(self, event_data: Dict[str, Any]) -> None:
        """Handler for GEM_SHUTDOWN event to gracefully stop task checks."""
        self.logger.info("Recebido GEM_SHUTDOWN. A parar as verifica√ß√µes de tarefas.")
        self.shutdown()

    async def _load_tasks_from_storage(self) -> None:
        """Loads to-do tasks from persistent storage."""
        try:
            tasks_data = await self.storage.get_setting(self.STORAGE_KEY, [])
            for task_dict in tasks_data:
                try:
                    task = TodoTask.from_dict(task_dict)
                    self._tasks[task.id] = task
                except Exception as e:
                    self.logger.error(f"Erro ao carregar tarefa do armazenamento: {e} - Dados: {task_dict}", exc_info=True)
            self.logger.info(f"Carregadas {len(self._tasks)} tarefas do armazenamento.")
        except Exception as e:
            self.logger.error(f"Falha ao carregar tarefas do armazenamento: {e}", exc_info=True)
        finally:
            self._tasks_loaded.set() # Sinaliza que as tarefas foram carregadas

    async def _save_tasks_to_storage(self) -> None:
        """Saves current to-do tasks to persistent storage."""
        try:
            tasks_data = [task.to_dict() for task in self._tasks.values()]
            await self.storage.set_setting(self.STORAGE_KEY, tasks_data)
            self.logger.debug(f"Salvas {len(self._tasks)} tarefas para o armazenamento.")
        except Exception as e:
            self.logger.error(f"Falha ao salvar tarefas no armazenamento: {e}", exc_info=True)

    async def _periodic_task_check(self) -> None:
        """Periodically checks for upcoming task deadlines and sends reminders."""
        self.logger.debug("Loop de verifica√ß√£o peri√≥dica de tarefas iniciado.")
        await self._tasks_loaded.wait() # Wait until tasks are loaded
        while True:
            try:
                await self._check_upcoming_deadlines()
                await asyncio.sleep(self._check_interval_seconds)
            except asyncio.CancelledError:
                self.logger.info("Tarefa de verifica√ß√£o peri√≥dica de tarefas cancelada.")
                break
            except Exception as e:
                self.logger.error(f"Erro no loop de verifica√ß√£o de tarefas: {e}", exc_info=True)
                await asyncio.sleep(self._check_interval_seconds * 2) # Wait longer on error

    async def _check_upcoming_deadlines(self) -> None:
        """Checks for tasks with upcoming due dates and notifies the user."""
        now = datetime.now()
        for task_id, task in list(self._tasks.items()):
            if not task.is_completed and task.due_date:
                time_until_due = task.due_date - now
                # Remind for tasks due within the next hour (and not already reminded in this check interval)
                if timedelta(0) < time_until_due <= timedelta(hours=1) and \
                   (task.due_date - timedelta(minutes=self._check_interval_seconds / 60)).date() != now.date(): # Check if it's a new reminder since last check
                    message = f"Lembrete: A tarefa '{task.description}' tem prazo √†s {task.due_date.strftime('%H:%M')}!"
                    await self.notification_manager.add_notification(message, level=NOTIFICATION_WARNING, vocalize=True)
                    await self.tts_module.speak(message)
                    self.logger.info(f"Lembrete enviado para a tarefa '{task.description}'.")
                    await self.event_manager.publish("TODO_TASK_REMINDER", task.to_dict())
                elif time_until_due <= timedelta(0) and not task.is_completed:
                    message = f"ATEN√á√ÉO: A tarefa '{task.description}' est√° atrasada!"
                    await self.notification_manager.add_notification(message, level=NOTIFICATION_ERROR, vocalize=True)
                    await self.tts_module.speak(message)
                    self.logger.warning(f"Tarefa '{task.description}' est√° atrasada.")
                    await self.event_manager.publish("TODO_TASK_OVERDUE", task.to_dict())


    # --------------------------------------------------------------------- Commands

    async def _add_task_command(self, description: str, due_date: Optional[str] = None, priority: int = 0) -> Dict[str, Any]:
        """
        Adiciona uma nova tarefa √† lista de afazeres.
        `due_date` deve ser uma string no formato ISO 8601 (YYYY-MM-DD HH:MM).
        `priority` pode ser 0 (Baixa), 1 (M√©dia) ou 2 (Alta).
        """
        await self._tasks_loaded.wait()

        parsed_due_date: Optional[datetime] = None
        if due_date:
            try:
                parsed_due_date = datetime.fromisoformat(due_date)
            except ValueError:
                await self._speak_response("Formato de data/hora inv√°lido para o prazo. Por favor, use 'AAAA-MM-DD HH:MM'.")
                return {"success": False, "output": "Formato de data/hora inv√°lido.", "error": "Invalid date/time format"}

        if not (0 <= priority <= 2):
            await self._speak_response("A prioridade deve ser 0 (Baixa), 1 (M√©dia) ou 2 (Alta).")
            return {"success": False, "output": "Prioridade inv√°lida.", "error": "Invalid priority value"}

        task_id = str(uuid.uuid4())
        new_task = TodoTask(
            id=task_id,
            description=description,
            due_date=parsed_due_date,
            priority=priority,
            is_completed=False
        )
        self._tasks[task_id] = new_task
        await self._save_tasks_to_storage()
        
        message = f"Tarefa '{description}' adicionada com sucesso. Prazo: {new_task.due_date.strftime('%Y-%m-%d %H:%M') if new_task.due_date else 'N/A'}."
        await self._speak_response(message)
        await self.notification_manager.add_notification(message, level=NOTIFICATION_SUCCESS)
        await self.event_manager.publish("TODO_TASK_ADDED", new_task.to_dict())
        self.logger.info(message)
        return {"success": True, "output": message, "error": None}

    async def _list_tasks_command(self, status: str = "pending", limit: int = 5) -> Dict[str, Any]:
        """
        Lista tarefas com base no seu status.
        `status` pode ser "pending" (pendente), "completed" (conclu√≠da) ou "all" (todas).
        """
        await self._tasks_loaded.wait()

        filtered_tasks: List[TodoTask] = []
        for task in self._tasks.values():
            if status == "all":
                filtered_tasks.append(task)
            elif status == "pending" and not task.is_completed:
                filtered_tasks.append(task)
            elif status == "completed" and task.is_completed:
                filtered_tasks.append(task)
        
        # Sort by priority (high to low), then by due date (soonest first)
        filtered_tasks.sort(key=lambda t: (t.priority, t.due_date if t.due_date else datetime.max), reverse=True)
        
        tasks_to_display = filtered_tasks[:limit]

        if not tasks_to_display:
            message = f"N√£o h√° tarefas '{status}' para listar."
            await self._speak_response(message)
            return {"success": True, "output": message, "error": None}
        
        output_lines = [f"Tarefas ({status}):"]
        priority_map = {0: "Baixa", 1: "M√©dia", 2: "Alta"}
        for i, task in enumerate(tasks_to_display):
            due_date_str = task.due_date.strftime('%Y-%m-%d %H:%M') if task.due_date else 'N/A'
            completion_status = "‚úÖ Conclu√≠da" if task.is_completed else "‚è≥ Pendente"
            output_lines.append(f"{i+1}. {task.description} - Prioridade: {priority_map[task.priority]} - Prazo: {due_date_str} {completion_status}")
            output_lines.append(f"   (ID: {task.id[:8]}...)")
            output_lines.append("-" * 20)
        
        message = "\n".join(output_lines)
        await self._speak_response(f"As suas tarefas '{status}' foram listadas. Verifique o ecr√£ para os detalhes.")
        await self.notification_manager.add_notification(f"Lista de tarefas '{status}' exibida.", level=NOTIFICATION_INFO)
        return {"success": True, "output": message, "error": None}

    async def _mark_task_completed_command(self, task_id_prefix: str, completed: bool = True) -> Dict[str, Any]:
        """
        Marca uma tarefa como conclu√≠da ou pendente.
        Requer um prefixo do ID da tarefa.
        """
        await self._tasks_loaded.wait()

        task_to_update: Optional[TodoTask] = None
        matching_tasks = [t for t in self._tasks.values() if t.id.startswith(task_id_prefix)]

        if len(matching_tasks) == 1:
            task_to_update = matching_tasks[0]
        elif len(matching_tasks) > 1:
            message = f"M√∫ltiplas tarefas correspondem ao ID '{task_id_prefix}'. Por favor, seja mais espec√≠fico."
            await self._speak_response(message)
            return {"success": False, "output": message, "error": "Multiple matches"}
        else:
            message = f"Nenhuma tarefa encontrada com o ID '{task_id_prefix}'."
            await self._speak_response(message)
            return {"success": False, "output": message, "error": "Task not found"}

        if task_to_update:
            task_to_update.is_completed = completed
            await self._save_tasks_to_storage()

            status_text = "conclu√≠da" if completed else "marcada como pendente novamente"
            message = f"Tarefa '{task_to_update.description}' (ID: {task_to_update.id[:8]}...) {status_text}."
            await self._speak_response(message)
            await self.notification_manager.add_notification(message, level=NOTIFICATION_SUCCESS)
            await self.event_manager.publish("TODO_TASK_UPDATED", task_to_update.to_dict())
            self.logger.info(message)
            return {"success": True, "output": message, "error": None}
        
        return {"success": False, "output": "Erro desconhecido ao atualizar tarefa.", "error": "Unknown error"}

    async def _update_task_details_command(self, task_id_prefix: str, new_description: Optional[str] = None,
                                          new_due_date: Optional[str] = None, new_priority: Optional[int] = None) -> Dict[str, Any]:
        """
        Atualiza detalhes de uma tarefa existente.
        Requer um prefixo do ID da tarefa.
        """
        await self._tasks_loaded.wait()

        task_to_update: Optional[TodoTask] = None
        matching_tasks = [t for t in self._tasks.values() if t.id.startswith(task_id_prefix)]

        if len(matching_tasks) == 1:
            task_to_update = matching_tasks[0]
        elif len(matching_tasks) > 1:
            message = f"M√∫ltiplas tarefas correspondem ao ID '{task_id_prefix}'. Por favor, seja mais espec√≠fico."
            await self._speak_response(message)
            return {"success": False, "output": message, "error": "Multiple matches"}
        else:
            message = f"Nenhuma tarefa encontrada com o ID '{task_id_prefix}'."
            await self._speak_response(message)
            return {"success": False, "output": message, "error": "Task not found"}

        if task_to_update:
            if new_description: task_to_update.description = new_description
            
            if new_due_date:
                try:
                    task_to_update.due_date = datetime.fromisoformat(new_due_date)
                except ValueError:
                    await self._speak_response("Formato de data/hora inv√°lido para o novo prazo. Por favor, use 'AAAA-MM-DD HH:MM'.")
                    return {"success": False, "output": "Formato de data/hora inv√°lido.", "error": "Invalid date/time format"}
            
            if new_priority is not None:
                if not (0 <= new_priority <= 2):
                    await self._speak_response("A nova prioridade deve ser 0 (Baixa), 1 (M√©dia) ou 2 (Alta).")
                    return {"success": False, "output": "Prioridade inv√°lida.", "error": "Invalid priority value"}
                task_to_update.priority = new_priority
            
            await self._save_tasks_to_storage()
            message = f"Tarefa '{task_to_update.description}' (ID: {task_to_update.id[:8]}...) atualizada com sucesso."
            await self._speak_response(message)
            await self.notification_manager.add_notification(message, level=NOTIFICATION_SUCCESS)
            await self.event_manager.publish("TODO_TASK_UPDATED", task_to_update.to_dict())
            self.logger.info(message)
            return {"success": True, "output": message, "error": None}
        
        return {"success": False, "output": "Erro desconhecido ao atualizar detalhes da tarefa.", "error": "Unknown error"}

    async def _delete_task_command(self, task_id_prefix: str) -> Dict[str, Any]:
        """
        Remove uma tarefa da lista de afazeres.
        Requer um prefixo do ID da tarefa.
        """
        await self._tasks_loaded.wait()

        task_to_delete: Optional[TodoTask] = None
        matching_tasks = [t for t in self._tasks.values() if t.id.startswith(task_id_prefix)]

        if len(matching_tasks) == 1:
            task_to_delete = matching_tasks[0]
        elif len(matching_tasks) > 1:
            message = f"M√∫ltiplas tarefas correspondem ao ID '{task_id_prefix}'. Por favor, seja mais espec√≠fico."
            await self._speak_response(message)
            return {"success": False, "output": message, "error": "Multiple matches"}
        else:
            message = f"Nenhuma tarefa encontrada com o ID '{task_id_prefix}' para remo√ß√£o."
            await self._speak_response(message)
            return {"success": False, "output": message, "error": "Task not found"}

        if task_to_delete:
            del self._tasks[task_to_delete.id]
            await self._save_tasks_to_storage()
            message = f"Tarefa '{task_to_delete.description}' (ID: {task_to_delete.id[:8]}...) removida."
            await self._speak_response(message)
            await self.notification_manager.add_notification(message, level=NOTIFICATION_SUCCESS)
            await self.event_manager.publish("TODO_TASK_DELETED", {"task_id": task_to_delete.id})
            self.logger.info(message)
            return {"success": True, "output": message, "error": None}
        
        return {"success": False, "output": "Erro desconhecido ao remover tarefa.", "error": "Unknown error"}

    # --------------------------------------------------------------------- Plugin Interface

    def register_commands(self, executor: CommandExecutor) -> None:
        """Registers to-do management commands with the CommandExecutor."""
        self.logger.info("A registar comandos do plugin TodoManager...")
        executor.register_command("add_task", self._add_task_command)
        executor.register_command("list_tasks", self._list_tasks_command)
        executor.register_command("mark_task_completed", self._mark_task_completed_command)
        executor.register_command("update_task_details", self._update_task_details_command)
        executor.register_command("delete_task", self._delete_task_command)
        self.logger.info("Comandos TodoManager registados.")

    def get_tools_schema(self) -> List[Dict[str, Any]]:
        """
        Returns a list of tool definitions (schemas) for to-do list features.
        These schemas are exposed to the LLM for function calling.
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": "add_task",
                    "description": "Adiciona uma nova tarefa √† lista de afazeres do usu√°rio. Pode incluir um prazo e uma prioridade.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "description": {
                                "type": "string",
                                "description": "A descri√ß√£o da tarefa a ser adicionada.",
                            },
                            "due_date": {
                                "type": "string",
                                "description": "O prazo para a tarefa no formato ISO 8601 (YYYY-MM-DD HH:MM). Opcional.",
                            },
                            "priority": {
                                "type": "integer",
                                "description": "A prioridade da tarefa: 0 para Baixa, 1 para M√©dia, 2 para Alta. Padr√£o para 0.",
                                "enum": [0, 1, 2],
                                "default": 0
                            }
                        },
                        "required": ["description"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "list_tasks",
                    "description": "Lista as tarefas da lista de afazeres do usu√°rio. Pode filtrar por status ('pending', 'completed', 'all') e limitar o n√∫mero de resultados.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "status": {
                                "type": "string",
                                "description": "O status das tarefas a listar: 'pending' (pendente), 'completed' (conclu√≠da) ou 'all' (todas). Padr√£o para 'pending'.",
                                "enum": ["pending", "completed", "all"],
                                "default": "pending"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "O n√∫mero m√°ximo de tarefas a retornar. Padr√£o para 5.",
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
                    "name": "mark_task_completed",
                    "description": "Marca uma tarefa existente como conclu√≠da ou a retorna para o status pendente. Requer o ID completo ou um prefixo √∫nico da tarefa.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "task_id_prefix": {
                                "type": "string",
                                "description": "O ID completo ou um prefixo √∫nico da tarefa a ser marcada.",
                            },
                            "completed": {
                                "type": "boolean",
                                "description": "Defina para 'true' para marcar como conclu√≠da, 'false' para marcar como pendente. Padr√£o para 'true'.",
                                "default": True
                            }
                        },
                        "required": ["task_id_prefix"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "update_task_details",
                    "description": "Atualiza os detalhes de uma tarefa existente. Requer o ID completo ou um prefixo √∫nico da tarefa. Pode atualizar a descri√ß√£o, o prazo e a prioridade.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "task_id_prefix": {
                                "type": "string",
                                "description": "O ID completo ou um prefixo √∫nico da tarefa a ser atualizada.",
                            },
                            "new_description": {
                                "type": "string",
                                "description": "Uma nova descri√ß√£o para a tarefa. Opcional.",
                            },
                            "new_due_date": {
                                "type": "string",
                                "description": "Um novo prazo para a tarefa no formato ISO 8601 (YYYY-MM-DD HH:MM). Opcional.",
                            },
                            "new_priority": {
                                "type": "integer",
                                "description": "Uma nova prioridade para a tarefa: 0 (Baixa), 1 (M√©dia), 2 (Alta). Opcional.",
                                "enum": [0, 1, 2]
                            }
                        },
                        "required": ["task_id_prefix"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "delete_task",
                    "description": "Remove uma tarefa da lista de afazeres. Requer o ID completo ou um prefixo √∫nico da tarefa. Esta a√ß√£o √© irrevers√≠vel.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "task_id_prefix": {
                                "type": "string",
                                "description": "O ID completo ou um prefixo √∫nico da tarefa a ser removida.",
                            },
                        },
                        "required": ["task_id_prefix"],
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
        self.logger.info("TodoManager a ser desligado. A parar a tarefa de verifica√ß√£o de tarefas.")
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
    logger = logging.getLogger("TestTodoManager")

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

    async def run_todo_manager_tests():
        print("\n--- Iniciando Testes do TodoManager ---")

        dummy_gem = DummyGEM(logger)
        todo_manager = TodoManager(dummy_gem, logger)
        
        todo_manager.register_commands(dummy_gem.command_executor)

        await todo_manager.initialize()

        now = datetime.now()
        tomorrow_morning = (now + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
        yesterday_morning = (now - timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)

        # --- Teste 1: Adicionar Tarefa ---
        print("\n--- Teste 1: Adicionar Tarefa ---")
        result_add_task1 = await dummy_gem.command_executor.execute(
            "add_task",
            description="Comprar leite e p√£o",
            due_date=tomorrow_morning.isoformat(),
            priority=1 # M√©dia
        )
        print(result_add_task1["output"])
        assert result_add_task1["success"] is True
        assert "Tarefa 'Comprar leite e p√£o' adicionada com sucesso." in result_add_task1["output"]

        result_add_task2 = await dummy_gem.command_executor.execute(
            "add_task",
            description="Enviar relat√≥rio mensal",
            priority=2 # Alta
        )
        print(result_add_task2["output"])
        assert result_add_task2["success"] is True

        result_add_task3_overdue = await dummy_gem.command_executor.execute(
            "add_task",
            description="Pagar conta de luz",
            due_date=yesterday_morning.isoformat(),
            priority=2 # Alta
        )
        print(result_add_task3_overdue["output"])
        assert result_add_task3_overdue["success"] is True


        # --- Teste 2: Listar Tarefas Pendentes (padr√£o) ---
        print("\n--- Teste 2: Listar Tarefas Pendentes ---")
        result_list_pending = await dummy_gem.command_executor.execute("list_tasks")
        print(result_list_pending["output"])
        assert result_list_pending["success"] is True
        assert "Comprar leite e p√£o" in result_list_pending["output"]
        assert "Enviar relat√≥rio mensal" in result_list_pending["output"]
        assert "Pagar conta de luz" in result_list_pending["output"]
        assert "Prioridade: M√©dia" in result_list_pending["output"]
        assert "Prioridade: Alta" in result_list_pending["output"]


        # --- Teste 3: Marcar Tarefa como Conclu√≠da ---
        print("\n--- Teste 3: Marcar Tarefa como Conclu√≠da ---")
        task_id_to_complete = next(t.id for t in todo_manager._tasks.values() if t.description == "Comprar leite e p√£o")
        result_mark_complete = await dummy_gem.command_executor.execute("mark_task_completed", task_id_prefix=task_id_to_complete[:8])
        print(result_mark_complete["output"])
        assert result_mark_complete["success"] is True
        assert "Tarefa 'Comprar leite e p√£o' (ID:" in result_mark_complete["output"] and "conclu√≠da." in result_mark_complete["output"]

        # Verificar se n√£o aparece mais nas pendentes
        result_list_pending_after = await dummy_gem.command_executor.execute("list_tasks")
        print(result_list_pending_after["output"])
        assert "Comprar leite e p√£o" not in result_list_pending_after["output"]

        # --- Teste 4: Listar Tarefas Conclu√≠das ---
        print("\n--- Teste 4: Listar Tarefas Conclu√≠das ---")
        result_list_completed = await dummy_gem.command_executor.execute("list_tasks", status="completed")
        print(result_list_completed["output"])
        assert result_list_completed["success"] is True
        assert "Comprar leite e p√£o" in result_list_completed["output"]
        assert "‚úÖ Conclu√≠da" in result_list_completed["output"]

        # --- Teste 5: Atualizar Detalhes da Tarefa ---
        print("\n--- Teste 5: Atualizar Detalhes da Tarefa ---")
        task_id_to_update = next(t.id for t in todo_manager._tasks.values() if t.description == "Enviar relat√≥rio mensal")
        new_due_date_update = (now + timedelta(days=2)).replace(hour=17, minute=0, second=0, microsecond=0).isoformat()
        result_update = await dummy_gem.command_executor.execute(
            "update_task_details",
            task_id_prefix=task_id_to_update[:8],
            new_description="Preparar e enviar relat√≥rio trimestral",
            new_due_date=new_due_date_update,
            new_priority=0 # Baixa
        )
        print(result_update["output"])
        assert result_update["success"] is True
        assert "Tarefa 'Preparar e enviar relat√≥rio trimestral' (ID:" in result_update["output"] and "atualizada com sucesso." in result_update["output"]
        
        # Verify update
        updated_task = todo_manager._tasks[task_id_to_update]
        assert updated_task.description == "Preparar e enviar relat√≥rio trimestral"
        assert updated_task.due_date.isoformat() == new_due_date_update
        assert updated_task.priority == 0

        # --- Teste 6: Remover Tarefa ---
        print("\n--- Teste 6: Remover Tarefa ---")
        task_id_to_delete = next(t.id for t in todo_manager._tasks.values() if t.description == "Pagar conta de luz")
        result_delete = await dummy_gem.command_executor.execute("delete_task", task_id_prefix=task_id_to_delete[:8])
        print(result_delete["output"])
        assert result_delete["success"] is True
        assert "Tarefa 'Pagar conta de luz' (ID:" in result_delete["output"] and "removida." in result_delete["output"]
        
        # Verify deletion
        assert task_id_to_delete not in todo_manager._tasks

        print("\n--- Testes do TodoManager conclu√≠dos com sucesso. ---")
        todo_manager.shutdown()
        await asyncio.sleep(0.1) # Give shutdown task a moment
        assert todo_manager._check_task is None or todo_manager._check_task.done()

    asyncio.run(run_todo_manager_tests())

