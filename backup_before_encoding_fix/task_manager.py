#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
💎 GEM OS - Task Manager (core/task_manager.py)
Manages user tasks, reminders, and scheduling.

Responsibilities
----------------
- Create, retrieve, update, and delete tasks/reminders.
- Schedule and trigger notifications for due tasks.
- Persist tasks using the Storage module.
- Integrate with NotificationManager for alerts.
- Expose task management capabilities as tools for the LLM.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
import schedule # Usado para agendamento em segundo plano
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable, Awaitable, Tuple

from core.plugins import BasePlugin, CommandExecutor, GEMVoiceAssistant
from core.notification_manager import NotificationManager, NOTIFICATION_INFO, NOTIFICATION_WARNING, NOTIFICATION_SUCCESS

# Forward declarations for type hinting, actual objects passed at runtime
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

# --- Dataclass para Tarefa ---
@dataclass
class Task:
    id: str
    description: str
    due_time: Optional[datetime] = None
    is_completed: bool = False
    is_recurring: bool = False # Simplificado; implementações mais complexas teriam padrões de recorrência
    last_triggered: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "due_time": self.due_time.isoformat() if self.due_time else None,
            "is_completed": self.is_completed,
            "is_recurring": self.is_recurring,
            "last_triggered": self.last_triggered.isoformat() if self.last_triggered else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Task:
        return cls(
            id=data["id"],
            description=data["description"],
            due_time=datetime.fromisoformat(data["due_time"]) if data["due_time"] else None,
            is_completed=data["is_completed"],
            is_recurring=data["is_recurring"],
            last_triggered=datetime.fromisoformat(data["last_triggered"]) if data["last_triggered"] else None,
        )

# --- Task Manager como um Plugin ---
class TaskManager(BasePlugin):
    """
    Manages user-defined tasks and reminders for GEM OS.
    Integrates with Storage for persistence and NotificationManager for alerts.
    """
    STORAGE_KEY = "user_tasks"

    def __init__(self, gem_instance: GEMVoiceAssistant, logger: Optional[logging.Logger] = None):
        super().__init__(gem_instance, logger)
        self.logger.info("TaskManager plugin inicializado.")
        
        self.event_manager: EventManager = gem_instance.event_manager
        self.notification_manager: NotificationManager = gem_instance.notification_manager
        self.storage: Storage = gem_instance.storage
        self.tts_module: TTSModule = gem_instance.tts_module

        self._tasks: Dict[str, Task] = {} # {task_id: Task_object}
        self._scheduler_thread: Optional[threading.Thread] = None
        self._is_scheduler_running: bool = False

        self._tasks_loaded = asyncio.Event() # Evento para sinalizar que as tarefas foram carregadas

    async def initialize(self) -> None:
        """Loads tasks from storage and starts the background scheduler."""
        await self._load_tasks_from_storage()
        self._start_scheduler()
        self.event_manager.subscribe("GEM_SHUTDOWN", self._on_gem_shutdown)
        self.logger.info("TaskManager inicializado e agendador iniciado.")

    async def _on_gem_shutdown(self, event_data: Dict[str, Any]) -> None:
        """Handler for GEM_SHUTDOWN event to gracefully stop the scheduler."""
        self.logger.info("Recebido GEM_SHUTDOWN. A desligar o agendador de tarefas.")
        self.shutdown()

    async def _load_tasks_from_storage(self) -> None:
        """Loads tasks from persistent storage."""
        try:
            tasks_data = await self.storage.get_setting(self.STORAGE_KEY, [])
            for task_dict in tasks_data:
                try:
                    task = Task.from_dict(task_dict)
                    self._tasks[task.id] = task
                except Exception as e:
                    self.logger.error(f"Erro ao carregar tarefa do armazenamento: {e} - Dados: {task_dict}", exc_info=True)
            self.logger.info(f"Carregadas {len(self._tasks)} tarefas do armazenamento.")
        except Exception as e:
            self.logger.error(f"Falha ao carregar tarefas do armazenamento: {e}", exc_info=True)
        finally:
            self._tasks_loaded.set() # Sinaliza que as tarefas foram carregadas

    async def _save_tasks_to_storage(self) -> None:
        """Saves current tasks to persistent storage."""
        try:
            tasks_data = [task.to_dict() for task in self._tasks.values()]
            await self.storage.set_setting(self.STORAGE_KEY, tasks_data)
            self.logger.debug(f"Salvas {len(self._tasks)} tarefas para o armazenamento.")
        except Exception as e:
            self.logger.error(f"Falha ao salvar tarefas no armazenamento: {e}", exc_info=True)

    def _start_scheduler(self) -> None:
        """Starts the background thread for the scheduler."""
        if not self._is_scheduler_running:
            self._is_scheduler_running = True
            self._scheduler_thread = threading.Thread(target=self._run_scheduler_loop, daemon=True)
            self._scheduler_thread.start()
            self.logger.info("Agendador de tarefas em segundo plano iniciado.")
            schedule.every(10).seconds.do(lambda: asyncio.run_coroutine_threadsafe(self._check_due_tasks(), asyncio.get_event_loop()))
            # schedule.every().day.at("08:00").do(lambda: asyncio.run_coroutine_threadsafe(self._check_daily_tasks(), asyncio.get_event_loop()))

    def _run_scheduler_loop(self) -> None:
        """The main loop for the schedule library."""
        self.logger.debug("Loop do agendador iniciado.")
        while self._is_scheduler_running:
            try:
                schedule.run_pending()
                time.sleep(1) # Check every second
            except Exception as e:
                self.logger.error(f"Erro no loop do agendador: {e}", exc_info=True)
                time.sleep(5) # Wait before retrying
        self.logger.debug("Loop do agendador terminado.")

    async def _check_due_tasks(self) -> None:
        """Checks for tasks that are due and triggers notifications."""
        await self._tasks_loaded.wait() # Ensure tasks are loaded before checking
        
        now = datetime.now()
        for task_id, task in list(self._tasks.items()): # Iterate on a copy as tasks might be modified
            if not task.is_completed and task.due_time and task.due_time <= now:
                if not task.last_triggered or (now - task.last_triggered) > timedelta(minutes=1): # Prevent rapid re-triggering
                    self.logger.info(f"Tarefa '{task.description}' com vencimento agora.")
                    await self.notification_manager.add_notification(
                        f"Lembrete: A tarefa '{task.description}' está com vencimento agora!",
                        level=NOTIFICATION_WARNING, vocalize=True
                    )
                    await self.tts_module.speak(f"Lembrete: {task.description} está com vencimento agora!")
                    task.last_triggered = now
                    # Para tarefas não recorrentes, considere marcá-las como concluídas ou reagendá-las
                    if not task.is_recurring:
                        self.logger.info(f"Tarefa não recorrente '{task.description}' vencida. Marcar como concluída para evitar novos alertas.")
                        task.is_completed = True # Ou perguntar ao usuário se deseja concluir/reagendar
                    await self._save_tasks_to_storage()
                    await self.event_manager.publish("TASK_REMINDER_TRIGGERED", task.to_dict())

    # --------------------------------------------------------------------- Commands

    async def _add_task_command(self, description: str, due_time: Optional[str] = None, is_recurring: bool = False) -> Dict[str, Any]:
        """
        Adiciona uma nova tarefa ou lembrete.
        due_time pode ser uma string como "2025-12-31 14:30" ou "amanhã 10:00".
        """
        await self._tasks_loaded.wait() # Garante que as tarefas foram carregadas
        task_id = str(uuid.uuid4())
        parsed_due_time: Optional[datetime] = None

        if due_time:
            try:
                # Tentativa de parsear data/hora (pode ser expandido com uma lib de parseamento de linguagem natural)
                if "amanhã" in due_time.lower():
                    # Parseamento básico de "amanhã HH:MM"
                    time_part = due_time.lower().replace("amanhã", "").strip()
                    if time_part:
                        today = datetime.now().date()
                        tomorrow = today + timedelta(days=1)
                        parsed_due_time = datetime.combine(tomorrow, datetime.strptime(time_part, "%H:%M").time())
                    else:
                        parsed_due_time = datetime.now() + timedelta(days=1) # Amanhã na hora atual
                else:
                    parsed_due_time = datetime.fromisoformat(due_time) # Tenta ISO format como padrão
            except ValueError:
                await self._speak_response(f"Formato de data/hora inválido para '{due_time}'. Por favor, use 'AAAA-MM-DD HH:MM' ou 'amanhã HH:MM'.")
                return {"success": False, "output": "Formato de data/hora inválido.", "error": "Invalid date/time format"}

        task = Task(id=task_id, description=description, due_time=parsed_due_time, is_recurring=is_recurring)
        self._tasks[task.id] = task
        await self._save_tasks_to_storage()
        
        message = f"Tarefa adicionada: '{description}'. "
        if task.due_time:
            message += f"Com vencimento em {task.due_time.strftime('%Y-%m-%d %H:%M')}. "
        if task.is_recurring:
            message += "É uma tarefa recorrente."

        await self._speak_response(message)
        await self.notification_manager.add_notification(message, level=NOTIFICATION_INFO)
        await self.event_manager.publish("TASK_CREATED", task.to_dict())
        self.logger.info(message)
        return {"success": True, "output": message, "error": None}

    async def _list_tasks_command(self, status: str = "pending") -> Dict[str, Any]:
        """Lista tarefas com base no seu status (pending, completed, all)."""
        await self._tasks_loaded.wait() # Garante que as tarefas foram carregadas
        
        filtered_tasks = []
        for task in self._tasks.values():
            if status == "all" or \
               (status == "pending" and not task.is_completed) or \
               (status == "completed" and task.is_completed):
                filtered_tasks.append(task)
        
        if not filtered_tasks:
            message = f"Não há tarefas com o status '{status}'."
            await self._speak_response(message)
            return {"success": True, "output": message, "error": None}

        output_lines = [f"Suas tarefas com status '{status}':"]
        for i, task in enumerate(filtered_tasks):
            due_info = f" (Vence: {task.due_time.strftime('%Y-%m-%d %H:%M')})" if task.due_time else ""
            completed_info = " [COMPLETA]" if task.is_completed else ""
            recurring_info = " [RECORRENTE]" if task.is_recurring else ""
            output_lines.append(f"{i+1}. {task.description}{due_info}{completed_info}{recurring_info} (ID: {task.id[:8]}...)")
        
        message = "\n".join(output_lines)
        await self._speak_response(f"As suas tarefas com status {status} foram listadas. Verifique o ecrã para os detalhes.")
        await self.notification_manager.add_notification(f"Tarefas listadas: {status}", level=NOTIFICATION_INFO)
        return {"success": True, "output": message, "error": None}

    async def _complete_task_command(self, task_id_prefix: str) -> Dict[str, Any]:
        """Marca uma tarefa como concluída usando um prefixo do ID."""
        await self._tasks_loaded.wait() # Garante que as tarefas foram carregadas
        
        task_to_complete: Optional[Task] = None
        matching_tasks = [t for t in self._tasks.values() if t.id.startswith(task_id_prefix)]

        if len(matching_tasks) == 1:
            task_to_complete = matching_tasks[0]
        elif len(matching_tasks) > 1:
            message = f"Múltiplas tarefas correspondem ao ID '{task_id_prefix}'. Por favor, seja mais específico."
            await self._speak_response(message)
            return {"success": False, "output": message, "error": "Multiple matches"}
        else:
            message = f"Nenhuma tarefa encontrada com o ID '{task_id_prefix}'."
            await self._speak_response(message)
            return {"success": False, "output": message, "error": "Task not found"}

        if task_to_complete and not task_to_complete.is_completed:
            task_to_complete.is_completed = True
            await self._save_tasks_to_storage()
            message = f"Tarefa '{task_to_complete.description}' marcada como concluída."
            await self._speak_response(message)
            await self.notification_manager.add_notification(message, level=NOTIFICATION_SUCCESS)
            await self.event_manager.publish("TASK_COMPLETED", task_to_complete.to_dict())
            self.logger.info(message)
            return {"success": True, "output": message, "error": None}
        elif task_to_complete and task_to_complete.is_completed:
            message = f"A tarefa '{task_to_complete.description}' já está concluída."
            await self._speak_response(message)
            return {"success": False, "output": message, "error": "Task already completed"}
        
        return {"success": False, "output": "Erro desconhecido ao completar tarefa.", "error": "Unknown error"}


    async def _delete_task_command(self, task_id_prefix: str) -> Dict[str, Any]:
        """Remove uma tarefa usando um prefixo do ID."""
        await self._tasks_loaded.wait() # Garante que as tarefas foram carregadas
        
        task_to_delete: Optional[Task] = None
        matching_tasks = [t for t in self._tasks.values() if t.id.startswith(task_id_prefix)]

        if len(matching_tasks) == 1:
            task_to_delete = matching_tasks[0]
        elif len(matching_tasks) > 1:
            message = f"Múltiplas tarefas correspondem ao ID '{task_id_prefix}'. Por favor, seja mais específico."
            await self._speak_response(message)
            return {"success": False, "output": message, "error": "Multiple matches"}
        else:
            message = f"Nenhuma tarefa encontrada com o ID '{task_id_prefix}'."
            await self._speak_response(message)
            return {"success": False, "output": message, "error": "Task not found"}

        if task_to_delete:
            del self._tasks[task_to_delete.id]
            await self._save_tasks_to_storage()
            message = f"Tarefa '{task_to_delete.description}' removida."
            await self._speak_response(message)
            await self.notification_manager.add_notification(message, level=NOTIFICATION_INFO)
            await self.event_manager.publish("TASK_DELETED", {"task_id": task_to_delete.id})
            self.logger.info(message)
            return {"success": True, "output": message, "error": None}
        
        return {"success": False, "output": "Erro desconhecido ao remover tarefa.", "error": "Unknown error"}

    # --------------------------------------------------------------------- Plugin Interface

    def register_commands(self, executor: CommandExecutor) -> None:
        """Registers task management commands with the CommandExecutor."""
        self.logger.info("A registar comandos do plugin TaskManager...")
        executor.register_command("add_task", self._add_task_command)
        executor.register_command("list_tasks", self._list_tasks_command)
        executor.register_command("complete_task", self._complete_task_command)
        executor.register_command("delete_task", self._delete_task_command)
        self.logger.info("Comandos TaskManager registados.")

    def get_tools_schema(self) -> List[Dict[str, Any]]:
        """
        Returns a list of tool definitions (schemas) for task management features.
        These schemas are exposed to the LLM for function calling.
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": "add_task",
                    "description": "Adiciona uma nova tarefa ou lembrete para o usuário. Peça sempre a descrição da tarefa. Pergunte pela data e hora de vencimento se não for fornecida. Pode ser recorrente.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "description": {
                                "type": "string",
                                "description": "Uma breve descrição da tarefa ou lembrete.",
                            },
                            "due_time": {
                                "type": "string",
                                "description": "A data e hora de vencimento da tarefa, no formato ISO 8601 (YYYY-MM-DD HH:MM), ou 'amanhã HH:MM'. Opcional.",
                            },
                            "is_recurring": {
                                "type": "boolean",
                                "description": "Define se a tarefa é recorrente. Padrão para falso.",
                                "default": False
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
                    "description": "Lista as tarefas do usuário com base no seu status. Pode listar tarefas 'pending' (pendentes), 'completed' (concluídas) ou 'all' (todas).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "status": {
                                "type": "string",
                                "description": "O status das tarefas a listar ('pending', 'completed', 'all'). Padrão é 'pending'.",
                                "enum": ["pending", "completed", "all"],
                                "default": "pending"
                            }
                        },
                        "required": [],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "complete_task",
                    "description": "Marca uma tarefa existente como concluída. Requer o ID completo da tarefa ou um prefixo suficientemente único.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "task_id_prefix": {
                                "type": "string",
                                "description": "O ID completo ou um prefixo único da tarefa a ser marcada como concluída.",
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
                    "description": "Remove uma tarefa existente. Requer o ID completo da tarefa ou um prefixo suficientemente único.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "task_id_prefix": {
                                "type": "string",
                                "description": "O ID completo ou um prefixo único da tarefa a ser removida.",
                            }
                        },
                        "required": ["task_id_prefix"],
                    },
                },
            },
        ]

    async def _speak_response(self, text: str) -> None:
        """Helper para vocalizar respostas através do módulo TTS principal do GEM."""
        if self.tts_module:
            await self.tts_module.speak(text)
        else:
            self.logger.warning(f"Módulo TTS não disponível para falar: '{text}'")

    def shutdown(self) -> None:
        """Stops the scheduler and performs cleanup."""
        self.logger.info("TaskManager a ser desligado. A parar o agendador.")
        self._is_scheduler_running = False
        schedule.clear() # Limpa todas as tarefas agendadas
        if self._scheduler_thread and self._scheduler_thread.is_alive():
            # Não há uma maneira limpa de forçar um thread de 'schedule' a parar imediatamente
            # Confia que ele terminará após a próxima verificação do loop.
            self.logger.debug("Aguardando o thread do agendador terminar (pode demorar até 1 segundo).")
            self._scheduler_thread.join(timeout=1.5)


# =============================================================================
# CLI Test
# =============================================================================

if __name__ == "__main__":
    import asyncio
    
    # Configure logging for standalone test
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger("TestTaskManager")

    # --- Dummy Implementations for testing ---
    class DummyEventManager:
        def __init__(self, logger):
            self.logger = logger
            self._listeners = defaultdict(list)
        async def publish(self, event_type: str, data: Optional[Dict[str, Any]] = None) -> None:
            self.logger.info(f"Dummy EventManager: Publicado '{event_type}' com {data}")
        def subscribe(self, event_type: str, listener: Callable) -> None:
            self._listeners[event_type].append(listener)
        def unsubscribe(self, event_type: str, listener: Callable) -> None:
            pass # Simplified for test

    class DummyNotificationManager:
        def __init__(self, logger):
            self.logger = logger
        async def add_notification(self, message: str, level: str = NOTIFICATION_INFO, vocalize: bool = True) -> None:
            self.logger.info(f"Dummy Notification: [{level.upper()}] {message} (Vocalize: {vocalize})")
            await asyncio.sleep(0.01)

    class DummyStorage:
        def __init__(self, logger):
            self.logger = logger
            self._data: Dict[str, Any] = {}
        async def get_setting(self, key: str, default: Any = None) -> Any:
            self.logger.info(f"Dummy Storage: A obter '{key}'")
            return self._data.get(key, default)
        async def set_setting(self, key: str, value: Any) -> bool:
            self.logger.info(f"Dummy Storage: A salvar '{key}'")
            self._data[key] = value
            return True
        async def clear_conversation_history(self) -> bool:
            return True

    class DummyTTSModule:
        def __init__(self, logger):
            self.logger = logger
        async def speak(self, text: str) -> None:
            self.logger.info(f"Dummy TTS: A falar: '{text}'")
            await asyncio.sleep(0.01)

    class DummyCommandExecutor: # Minimal for registration
        def __init__(self, logger):
            self.logger = logger
            self.commands = {}
        def register_command(self, name: str, func: Callable[..., Awaitable[Dict[str, Any]]], **kwargs) -> None:
            self.commands[name] = (func, kwargs)
            self.logger.info(f"Dummy CommandExecutor: Registou comando '{name}'.")
        async def execute(self, command_name: str, *args, **kwargs) -> Dict[str, Any]:
            self.logger.info(f"Dummy CommandExecutor: A executar '{command_name}' com args={args}, kwargs={kwargs}")
            if command_name == "add_task":
                return await self._dummy_add_task(*args, **kwargs)
            elif command_name == "list_tasks":
                return await self._dummy_list_tasks(*args, **kwargs)
            elif command_name == "complete_task":
                return await self._dummy_complete_task(*args, **kwargs)
            elif command_name == "delete_task":
                return await self._dummy_delete_task(*args, **kwargs)
            return {"success": False, "output": "", "error": "Comando desconhecido simulado."}

        # Mocked versions of TaskManager's commands for direct execution testing
        async def _dummy_add_task(self, description: str, due_time: Optional[str] = None, is_recurring: bool = False) -> Dict[str, Any]:
            logger.info(f"Dummy add_task: {description} {due_time} {is_recurring}")
            return {"success": True, "output": f"Tarefa '{description}' adicionada (simulada).", "error": None}
        async def _dummy_list_tasks(self, status: str = "pending") -> Dict[str, Any]:
            logger.info(f"Dummy list_tasks: {status}")
            return {"success": True, "output": "Tarefas simuladas listadas.", "error": None}
        async def _dummy_complete_task(self, task_id_prefix: str) -> Dict[str, Any]:
            logger.info(f"Dummy complete_task: {task_id_prefix}")
            return {"success": True, "output": f"Tarefa '{task_id_prefix}' concluída (simulada).", "error": None}
        async def _dummy_delete_task(self, task_id_prefix: str) -> Dict[str, Any]:
            logger.info(f"Dummy delete_task: {task_id_prefix}")
            return {"success": True, "output": f"Tarefa '{task_id_prefix}' removida (simulada).", "error": None}


    class DummyConfigManager:
        def __init__(self):
            self.config = type('GEMConfig', (), {
                'general': type('GeneralConfig', (), {
                    'max_notification_history': 5,
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
            self.storage = DummyStorage(logger_instance)
            self.tts_module = DummyTTSModule(logger_instance)
            self.config_manager = DummyConfigManager()
            self.command_executor = DummyCommandExecutor(logger_instance) # Será usado para registar comandos

    async def run_task_manager_tests():
        print("\n--- Iniciando Testes do TaskManager ---")

        dummy_gem = DummyGEM(logger)
        task_manager = TaskManager(dummy_gem, logger)
        
        # O TaskManager é um plugin, então seus comandos seriam registrados no CommandExecutor
        task_manager.register_commands(dummy_gem.command_executor)

        await task_manager.initialize() # Inicia o agendador

        print("\n--- Teste 1: Adicionar Tarefas ---")
        await dummy_gem.command_executor.execute("add_task", description="Comprar leite")
        await dummy_gem.command_executor.execute("add_task", description="Ligar para o médico", due_time=(datetime.now() + timedelta(seconds=10)).isoformat()) # Vence em 10s
        await dummy_gem.command_executor.execute("add_task", description="Pagar contas", due_time="amanhã 10:00")
        await dummy_gem.command_executor.execute("add_task", description="Exercício diário", is_recurring=True)
        await asyncio.sleep(0.1) # Give time for tasks to be processed/saved

        print("\n--- Teste 2: Listar Tarefas Pendentes ---")
        result_list_pending = await dummy_gem.command_executor.execute("list_tasks", status="pending")
        print(result_list_pending["output"])
        assert "Comprar leite" in result_list_pending["output"]
        assert "Ligar para o médico" in result_list_pending["output"]
        assert "Exercício diário" in result_list_pending["output"]

        print("\n--- Teste 3: Aguardar e verificar tarefa vencida ---")
        print("Aguardando 10 segundos para o lembrete 'Ligar para o médico'...")
        await asyncio.sleep(11) # Espera 11 segundos para garantir que a tarefa vence

        # A notificação e TTS devem ter ocorrido no fundo.
        # Verificar o histórico de notificações (dummy)
        notification_history = dummy_gem.notification_manager.get_notification_history(limit=10)
        assert any("Lembrete: A tarefa 'Ligar para o médico'" in n.message for n in notification_history)
        print("✅ Lembrete 'Ligar para o médico' verificado no histórico de notificações.")

        # Recarregar as tarefas para ver se o status 'is_completed' mudou para a tarefa não recorrente vencida
        await task_manager._load_tasks_from_storage()
        task_found = next((t for t in task_manager._tasks.values() if "Ligar para o médico" in t.description), None)
        assert task_found and task_found.is_completed # Deve ser concluída se não recorrente

        print("\n--- Teste 4: Listar Todas as Tarefas (incluindo concluídas) ---")
        result_list_all = await dummy_gem.command_executor.execute("list_tasks", status="all")
        print(result_list_all["output"])
        assert "Comprar leite" in result_list_all["output"]
        assert "Ligar para o médico" in result_list_all["output"] # Ainda visível, mas como concluída
        assert "Pagar contas" in result_list_all["output"]
        assert "Exercício diário" in result_list_all["output"]

        print("\n--- Teste 5: Completar Tarefa ---")
        # Precisamos de um ID real ou prefixo para completar
        task_id_for_completion = next((t.id for t in task_manager._tasks.values() if "Comprar leite" in t.description), None)
        assert task_id_for_completion
        result_complete = await dummy_gem.command_executor.execute("complete_task", task_id_prefix=task_id_for_completion[:8])
        print(result_complete["output"])
        assert "marcada como concluída" in result_complete["output"]
        
        await task_manager._load_tasks_from_storage() # Recarrega para verificar o estado
        assert next((t for t in task_manager._tasks.values() if "Comprar leite" in t.description), None).is_completed

        print("\n--- Teste 6: Remover Tarefa ---")
        task_id_for_deletion = next((t.id for t in task_manager._tasks.values() if "Pagar contas" in t.description), None)
        assert task_id_for_deletion
        result_delete = await dummy_gem.command_executor.execute("delete_task", task_id_prefix=task_id_for_deletion[:8])
        print(result_delete["output"])
        assert "removida" in result_delete["output"]
        
        await task_manager._load_tasks_from_storage() # Recarrega para verificar o estado
        assert not any("Pagar contas" in t.description for t in task_manager._tasks.values())

        print("\n--- Testes do TaskManager concluídos com sucesso. ---")
        task_manager.shutdown()
        await asyncio.sleep(0.5) # Give time for shutdown


    asyncio.run(run_task_manager_tests())


