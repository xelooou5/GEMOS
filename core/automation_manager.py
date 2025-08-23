#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
üíé GEM OS - Automation Manager (core/automation_manager.py)
Manages user-defined routines and automations based on triggers and sequences of actions.

Responsibilities
----------------
- Define and store automation routines (trigger + sequence of commands).
- Monitor triggers (time-based, event-based) and execute routines.
- Add, update, and remove routines.
- Persist routines using the Storage module.
- Expose automation capabilities as tools for the LLM.
- Publish automation-related events.
- Integrate with NotificationManager for alerts.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
import schedule # Para agendamento em segundo plano
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable, Awaitable, Tuple

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

# --- Dataclass para A√ß√£o da Rotina ---
@dataclass
class RoutineAction:
    command_name: str
    args: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "command_name": self.command_name,
            "args": self.args,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> RoutineAction:
        return cls(
            command_name=data["command_name"],
            args=data.get("args")
        )

# --- Dataclass para Rotina de Automa√ß√£o ---
@dataclass
class AutomationRoutine:
    id: str
    name: str
    trigger_type: str # "time_daily", "time_once", "event_based"
    trigger_value: Optional[str] = None # E.g., "08:00", "2025-12-31 14:30", "NEW_EMAIL_RECEIVED"
    actions: List[RoutineAction]
    is_enabled: bool = True
    last_triggered: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "trigger_type": self.trigger_type,
            "trigger_value": self.trigger_value,
            "actions": [action.to_dict() for action in self.actions],
            "is_enabled": self.is_enabled,
            "last_triggered": self.last_triggered.isoformat() if self.last_triggered else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AutomationRoutine:
        return cls(
            id=data["id"],
            name=data["name"],
            trigger_type=data["trigger_type"],
            trigger_value=data.get("trigger_value"),
            actions=[RoutineAction.from_dict(action_dict) for action_dict in data["actions"]],
            is_enabled=data.get("is_enabled", True),
            last_triggered=datetime.fromisoformat(data["last_triggered"]) if data.get("last_triggered") else None,
        )

# --- Automation Manager como um Plugin ---
class AutomationManager(BasePlugin):
    """
    Manages user-defined automation routines for GEM OS, acting as a plugin.
    """
    STORAGE_KEY = "gem_automation_routines"

    def __init__(self, gem_instance: GEMVoiceAssistant, logger: Optional[logging.Logger] = None):
        super().__init__(gem_instance, logger)
        self.logger.info("AutomationManager plugin inicializado.")
        
        self.event_manager: EventManager = gem_instance.event_manager
        self.notification_manager: NotificationManager = gem_instance.notification_manager
        self.storage: Storage = gem_instance.storage
        self.tts_module: TTSModule = gem_instance.tts_module
        self.command_executor: CommandExecutor = gem_instance.command_executor # Precisa para executar comandos

        self._routines: Dict[str, AutomationRoutine] = {} # {routine_id: AutomationRoutine_object}
        self._routines_loaded = asyncio.Event()
        self._scheduler_thread: Optional[threading.Thread] = None
        self._is_scheduler_running: bool = False
        self._event_listeners: Dict[str, List[Tuple[str, Callable]]] = defaultdict(list) # {event_type: [(routine_id, listener_func)]}


    async def initialize(self) -> None:
        """Loads routines from storage and starts the background scheduler."""
        await self._load_routines_from_storage()
        self._start_scheduler()
        self.event_manager.subscribe("GEM_SHUTDOWN", self._on_gem_shutdown)
        self.logger.info("AutomationManager inicializado e agendador iniciado.")

    async def _on_gem_shutdown(self, event_data: Dict[str, Any]) -> None:
        """Handler for GEM_SHUTDOWN event to gracefully stop the scheduler."""
        self.logger.info("Recebido GEM_SHUTDOWN. A desligar o agendador de automa√ß√£o.")
        self.shutdown()

    async def _load_routines_from_storage(self) -> None:
        """Loads automation routines from persistent storage."""
        try:
            routines_data = await self.storage.get_setting(self.STORAGE_KEY, [])
            for routine_dict in routines_data:
                try:
                    routine = AutomationRoutine.from_dict(routine_dict)
                    self._routines[routine.id] = routine
                    self._schedule_routine(routine) # Re-schedule loaded routines
                except Exception as e:
                    self.logger.error(f"Erro ao carregar rotina do armazenamento: {e} - Dados: {routine_dict}", exc_info=True)
            self.logger.info(f"Carregadas {len(self._routines)} rotinas de automa√ß√£o do armazenamento.")
        except Exception as e:
            self.logger.error(f"Falha ao carregar rotinas do armazenamento: {e}", exc_info=True)
        finally:
            self._routines_loaded.set() # Sinaliza que as rotinas foram carregadas

    async def _save_routines_to_storage(self) -> None:
        """Saves current automation routines to persistent storage."""
        try:
            routines_data = [routine.to_dict() for routine in self._routines.values()]
            await self.storage.set_setting(self.STORAGE_KEY, routines_data)
            self.logger.debug(f"Salvas {len(self._routines)} rotinas para o armazenamento.")
        except Exception as e:
            self.logger.error(f"Falha ao salvar rotinas no armazenamento: {e}", exc_info=True)

    def _start_scheduler(self) -> None:
        """Starts the background thread for the scheduler."""
        if not self._is_scheduler_running:
            self._is_scheduler_running = True
            self._scheduler_thread = threading.Thread(target=self._run_scheduler_loop, daemon=True)
            self._scheduler_thread.start()
            self.logger.info("Agendador de automa√ß√£o em segundo plano iniciado.")

    def _run_scheduler_loop(self) -> None:
        """The main loop for the schedule library."""
        self.logger.debug("Loop do agendador de automa√ß√£o iniciado.")
        while self._is_scheduler_running:
            try:
                schedule.run_pending()
                time.sleep(1) # Check every second
            except Exception as e:
                self.logger.error(f"Erro no loop do agendador de automa√ß√£o: {e}", exc_info=True)
                time.sleep(5) # Wait before retrying
        self.logger.debug("Loop do agendador de automa√ß√£o terminado.")

    def _schedule_routine(self, routine: AutomationRoutine) -> None:
        """Adds a routine to the scheduler based on its trigger type."""
        if not routine.is_enabled:
            self.logger.debug(f"Rotina '{routine.name}' desativada, n√£o ser√° agendada.")
            return

        if routine.trigger_type == "time_daily" and routine.trigger_value:
            schedule.every().day.at(routine.trigger_value).do(
                lambda r=routine: asyncio.run_coroutine_threadsafe(self._execute_routine_actions(r), asyncio.get_event_loop())
            ).tag(routine.id)
            self.logger.info(f"Rotina di√°ria '{routine.name}' agendada para {routine.trigger_value}.")
        
        elif routine.trigger_type == "time_once" and routine.trigger_value:
            # Para "time_once", agendamos um job para a data/hora exata.
            # Se for no futuro, agendamos; se for no passado, ignoramos ou executamos imediatamente se perto.
            try:
                trigger_dt = datetime.fromisoformat(routine.trigger_value)
                if trigger_dt > datetime.now():
                    # Calculamos o atraso e agendamos uma √∫nica vez
                    delay_seconds = (trigger_dt - datetime.now()).total_seconds()
                    if delay_seconds > 0:
                        self.logger.info(f"Rotina √∫nica '{routine.name}' agendada para daqui a {delay_seconds:.0f} segundos.")
                        schedule.every(delay_seconds).seconds.do(
                            lambda r=routine: asyncio.run_coroutine_threadsafe(self._execute_routine_actions_once(r), asyncio.get_event_loop())
                        ).tag(routine.id)._do_last = True # Execute job immediately after delay
                    else:
                        self.logger.warning(f"Rotina √∫nica '{routine.name}' com tempo de gatilho no passado. Ignorando.")
                else:
                     self.logger.warning(f"Rotina √∫nica '{routine.name}' com tempo de gatilho no passado. Ignorando.")
            except ValueError:
                self.logger.error(f"Formato de data/hora inv√°lido para rotina √∫nica '{routine.name}': {routine.trigger_value}")
        
        elif routine.trigger_type == "event_based" and routine.trigger_value:
            # Subscreve a eventos espec√≠ficos.
            listener_func = lambda event_data, r=routine: asyncio.create_task(self._on_event_trigger(r, event_data))
            self.event_manager.subscribe(routine.trigger_value, listener_func)
            self._event_listeners[routine.trigger_value].append((routine.id, listener_func))
            self.logger.info(f"Rotina baseada em evento '{routine.name}' subscrita ao evento '{routine.trigger_value}'.")
        
        else:
            self.logger.warning(f"Tipo de gatilho de rotina desconhecido ou inv√°lido para '{routine.name}': {routine.trigger_type}, Valor: {routine.trigger_value}")

    async def _execute_routine_actions(self, routine: AutomationRoutine) -> None:
        """Executes the actions defined in a routine."""
        if not routine.is_enabled:
            return

        self.logger.info(f"A executar rotina '{routine.name}' (ID: {routine.id[:8]}...).")
        await self.notification_manager.add_notification(
            f"A executar rotina: {routine.name}", level=NOTIFICATION_INFO, vocalize=True
        )
        await self.tts_module.speak(f"A executar rotina {routine.name}.")
        
        for action in routine.actions:
            self.logger.debug(f"Executando a√ß√£o: {action.command_name} com args: {action.args}")
            try:
                result = await self.command_executor.execute(action.command_name, **(action.args or {}))
                if not result.get("success"):
                    self.logger.error(f"A√ß√£o '{action.command_name}' na rotina '{routine.name}' falhou: {result.get('error')}")
                    await self.notification_manager.add_notification(
                        f"A√ß√£o '{action.command_name}' na rotina '{routine.name}' falhou: {result.get('error')}", level=NOTIFICATION_ERROR
                    )
                    await self.tts_module.speak(f"Falha na rotina {routine.name}, a√ß√£o {action.command_name}.")
                    # Decidir se deve parar a rotina ou continuar com outras a√ß√µes
                    # Por enquanto, continuamos, mas podemos adicionar uma flag na rotina
            except Exception as e:
                self.logger.error(f"Erro inesperado ao executar a√ß√£o '{action.command_name}' na rotina '{routine.name}': {e}", exc_info=True)
                await self.notification_manager.add_notification(
                    f"Erro inesperado na a√ß√£o '{action.command_name}' na rotina '{routine.name}': {e}", level=NOTIFICATION_ERROR
                )
                await self.tts_module.speak(f"Erro grave na rotina {routine.name}.")
        
        routine.last_triggered = datetime.now()
        await self._save_routines_to_storage()
        await self.event_manager.publish("AUTOMATION_ROUTINE_EXECUTED", routine.to_dict())
        self.logger.info(f"Rotina '{routine.name}' conclu√≠da.")
        await self.notification_manager.add_notification(
            f"Rotina '{routine.name}' conclu√≠da com sucesso.", level=NOTIFICATION_SUCCESS, vocalize=False
        )

    async def _execute_routine_actions_once(self, routine: AutomationRoutine) -> None:
        """Executa as a√ß√µes de uma rotina √∫nica vez e a remove do agendador."""
        await self._execute_routine_actions(routine)
        schedule.clear(routine.id) # Remove o job agendado
        self.logger.info(f"Rotina √∫nica '{routine.name}' executada e removida do agendador.")
        # Se for uma rotina time_once, podemos desativ√°-la ou exclu√≠-la ap√≥s a execu√ß√£o
        routine.is_enabled = False # Desativa ap√≥s uma execu√ß√£o
        await self._save_routines_to_storage()


    async def _on_event_trigger(self, routine: AutomationRoutine, event_data: Dict[str, Any]) -> None:
        """Handler for event-based triggers."""
        self.logger.debug(f"Evento '{routine.trigger_value}' disparou para rotina '{routine.name}'. Dados: {event_data}")
        await self._execute_routine_actions(routine)

    def _clear_routine_schedule(self, routine_id: str) -> None:
        """Removes a routine from the schedule library."""
        schedule.clear(routine_id)
        # Tamb√©m desinscreve de eventos se for o caso
        for event_type, listeners in list(self._event_listeners.items()): # Iterate on copy
            for r_id, listener_func in listeners:
                if r_id == routine_id:
                    self.event_manager.unsubscribe(event_type, listener_func)
                    self._event_listeners[event_type].remove((r_id, listener_func))
                    self.logger.debug(f"Rotina '{routine_id}' desubscrita do evento '{event_type}'.")


    # --------------------------------------------------------------------- Commands

    async def _create_automation_routine_command(self, name: str, trigger_type: str, trigger_value: Optional[str],
                                                actions_json: str, is_enabled: bool = True) -> Dict[str, Any]:
        """
        Cria uma nova rotina de automa√ß√£o.
        `actions_json` deve ser uma string JSON representando uma lista de objetos RoutineAction.
        Ex: '[{"command_name": "tell_time"}, {"command_name": "speak_text", "args": {"text": "Hora atual."}}]'
        """
        await self._routines_loaded.wait()

        try:
            raw_actions = json.loads(actions_json)
            actions = [RoutineAction.from_dict(ra) for ra in raw_actions]
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            await self._speak_response(f"Formato JSON de a√ß√µes inv√°lido: {e}. Certifique-se de que √© uma lista de objetos de a√ß√£o v√°lidos.")
            return {"success": False, "output": "Formato de a√ß√µes inv√°lido.", "error": str(e)}

        if not actions:
            await self._speak_response("Uma rotina deve ter pelo menos uma a√ß√£o.")
            return {"success": False, "output": "Rotina sem a√ß√µes.", "error": "Routine must have at least one action"}

        routine_id = str(uuid.uuid4())
        new_routine = AutomationRoutine(
            id=routine_id,
            name=name,
            trigger_type=trigger_type,
            trigger_value=trigger_value,
            actions=actions,
            is_enabled=is_enabled
        )
        self._routines[routine_id] = new_routine
        await self._save_routines_to_storage()
        self._schedule_routine(new_routine) # Schedule the new routine

        message = f"Rotina de automa√ß√£o '{name}' criada com sucesso."
        await self._speak_response(message)
        await self.notification_manager.add_notification(message, level=NOTIFICATION_SUCCESS)
        await self.event_manager.publish("AUTOMATION_ROUTINE_CREATED", new_routine.to_dict())
        self.logger.info(message)
        return {"success": True, "output": message, "error": None}

    async def _list_automation_routines_command(self) -> Dict[str, Any]:
        """
        Lista todas as rotinas de automa√ß√£o definidas.
        """
        await self._routines_loaded.wait()

        if not self._routines:
            message = "Nenhuma rotina de automa√ß√£o definida."
            await self._speak_response(message)
            return {"success": True, "output": message, "error": None}
        
        output_lines = ["Rotinas de Automa√ß√£o:"]
        for i, routine in enumerate(self._routines.values()):
            status = "Ativada" if routine.is_enabled else "Desativada"
            trigger = f"Gatilho: {routine.trigger_type} ({routine.trigger_value or 'N/A'})"
            last_triggered_info = f" √öltimo Acionamento: {routine.last_triggered.strftime('%Y-%m-%d %H:%M')}" if routine.last_triggered else ""
            output_lines.append(f"{i+1}. {routine.name} ({status}) - {trigger}{last_triggered_info} (ID: {routine.id[:8]}...)")
            for j, action in enumerate(routine.actions):
                output_lines.append(f"   A√ß√£o {j+1}: {action.command_name} {action.args or ''}")
            output_lines.append("-" * 20)
        
        message = "\n".join(output_lines)
        await self._speak_response(f"As suas rotinas de automa√ß√£o foram listadas. Verifique o ecr√£ para os detalhes.")
        await self.notification_manager.add_notification("Lista de rotinas de automa√ß√£o exibida.", level=NOTIFICATION_INFO)
        return {"success": True, "output": message, "error": None}

    async def _toggle_automation_routine_command(self, routine_id_prefix: str, enable: bool) -> Dict[str, Any]:
        """
        Ativa ou desativa uma rotina de automa√ß√£o.
        """
        await self._routines_loaded.wait()

        routine_to_toggle: Optional[AutomationRoutine] = None
        matching_routines = [r for r in self._routines.values() if r.id.startswith(routine_id_prefix)]

        if len(matching_routines) == 1:
            routine_to_toggle = matching_routines[0]
        elif len(matching_routines) > 1:
            message = f"M√∫ltiplas rotinas correspondem ao ID '{routine_id_prefix}'. Por favor, seja mais espec√≠fico."
            await self._speak_response(message)
            return {"success": False, "output": message, "error": "Multiple matches"}
        else:
            message = f"Nenhuma rotina encontrada com o ID '{routine_id_prefix}'."
            await self._speak_response(message)
            return {"success": False, "output": message, "error": "Routine not found"}
        
        if routine_to_toggle:
            routine_to_toggle.is_enabled = enable
            self._clear_routine_schedule(routine_to_toggle.id) # Clear existing schedule
            if enable:
                self._schedule_routine(routine_to_toggle) # Re-schedule if enabled
            await self._save_routines_to_storage()

            action = "ativada" if enable else "desativada"
            message = f"Rotina '{routine_to_toggle.name}' {action} com sucesso."
            await self._speak_response(message)
            await self.notification_manager.add_notification(message, level=NOTIFICATION_SUCCESS)
            await self.event_manager.publish("AUTOMATION_ROUTINE_TOGGLED", {"id": routine_to_toggle.id, "enabled": enable})
            self.logger.info(message)
            return {"success": True, "output": message, "error": None}
        
        return {"success": False, "output": "Erro desconhecido ao alternar rotina.", "error": "Unknown error"}


    async def _delete_automation_routine_command(self, routine_id_prefix: str) -> Dict[str, Any]:
        """
        Remove uma rotina de automa√ß√£o.
        """
        await self._routines_loaded.wait()

        routine_to_delete: Optional[AutomationRoutine] = None
        matching_routines = [r for r in self._routines.values() if r.id.startswith(routine_id_prefix)]

        if len(matching_routines) == 1:
            routine_to_delete = matching_routines[0]
        elif len(matching_routines) > 1:
            message = f"M√∫ltiplas rotinas correspondem ao ID '{routine_id_prefix}'. Por favor, seja mais espec√≠fico."
            await self._speak_response(message)
            return {"success": False, "output": message, "error": "Multiple matches"}
        else:
            message = f"Nenhuma rotina encontrada com o ID '{routine_id_prefix}' para remo√ß√£o."
            await self._speak_response(message)
            return {"success": False, "output": "", "error": "Routine not found"}

        if routine_to_delete:
            self._clear_routine_schedule(routine_to_delete.id) # Remove do agendador
            del self._routines[routine_to_delete.id]
            await self._save_routines_to_storage()

            message = f"Rotina '{routine_to_delete.name}' removida com sucesso."
            await self._speak_response(message)
            await self.notification_manager.add_notification(message, level=NOTIFICATION_SUCCESS)
            await self.event_manager.publish("AUTOMATION_ROUTINE_DELETED", {"id": routine_to_delete.id})
            self.logger.info(message)
            return {"success": True, "output": message, "error": None}
        
        return {"success": False, "output": "Erro desconhecido ao remover rotina.", "error": "Unknown error"}


    # --------------------------------------------------------------------- Plugin Interface

    def register_commands(self, executor: CommandExecutor) -> None:
        """Registers automation management commands with the CommandExecutor."""
        self.logger.info("A registar comandos do plugin AutomationManager...")
        executor.register_command("create_automation_routine", self._create_automation_routine_command)
        executor.register_command("list_automation_routines", self._list_automation_routines_command)
        executor.register_command("toggle_automation_routine", self._toggle_automation_routine_command)
        executor.register_command("delete_automation_routine", self._delete_automation_routine_command)
        self.logger.info("Comandos AutomationManager registados.")

    def get_tools_schema(self) -> List[Dict[str, Any]]:
        """
        Returns a list of tool definitions (schemas) for automation management features.
        These schemas are exposed to the LLM for function calling.
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": "create_automation_routine",
                    "description": "Cria uma nova rotina de automa√ß√£o com um nome, tipo de gatilho (time_daily, time_once, event_based) e uma lista de a√ß√µes a executar. As a√ß√µes devem ser fornecidas como uma string JSON de objetos de a√ß√£o.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "Um nome para a rotina (ex: 'Rotina de Bom Dia').",
                            },
                            "trigger_type": {
                                "type": "string",
                                "description": "O tipo de gatilho para a rotina. 'time_daily' para gatilhos di√°rios, 'time_once' para gatilhos √∫nicos, 'event_based' para gatilhos por evento do sistema.",
                                "enum": ["time_daily", "time_once", "event_based"]
                            },
                            "trigger_value": {
                                "type": "string",
                                "description": "O valor associado ao gatilho. Para 'time_daily', √© a hora (HH:MM). Para 'time_once', √© a data e hora (YYYY-MM-DD HH:MM). Para 'event_based', √© o nome do evento (ex: 'NEW_EMAIL_RECEIVED').",
                            },
                            "actions_json": {
                                "type": "string",
                                "description": "Uma string JSON que representa uma lista de a√ß√µes a serem executadas. Cada a√ß√£o √© um objeto com 'command_name' e 'args' (opcional). Ex: '[{\"command_name\": \"tell_time\"}, {\"command_name\": \"speak_text\", \"args\": {\"text\": \"Hora atual.\"}}]'",
                            },
                            "is_enabled": {
                                "type": "boolean",
                                "description": "Define se a rotina deve ser ativada imediatamente. Padr√£o para verdadeiro.",
                                "default": True
                            }
                        },
                        "required": ["name", "trigger_type", "actions_json"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "list_automation_routines",
                    "description": "Lista todas as rotinas de automa√ß√£o que foram definidas, mostrando os seus nomes, status, gatilhos e a√ß√µes.",
                    "parameters": {"type": "object", "properties": {}, "required": []},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "toggle_automation_routine",
                    "description": "Ativa ou desativa uma rotina de automa√ß√£o existente. Requer o ID completo ou um prefixo √∫nico da rotina.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "routine_id_prefix": {
                                "type": "string",
                                "description": "O ID completo ou um prefixo √∫nico da rotina a ser ativada/desativada.",
                            },
                            "enable": {
                                "type": "boolean",
                                "description": "Defina para 'true' para ativar a rotina, 'false' para desativar.",
                            }
                        },
                        "required": ["routine_id_prefix", "enable"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "delete_automation_routine",
                    "description": "Remove uma rotina de automa√ß√£o existente. Requer o ID completo ou um prefixo √∫nico da rotina. Esta a√ß√£o √© irrevers√≠vel.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "routine_id_prefix": {
                                "type": "string",
                                "description": "O ID completo ou um prefixo √∫nico da rotina a ser removida.",
                            },
                        },
                        "required": ["routine_id_prefix"],
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
        """Stops the scheduler and performs cleanup."""
        self.logger.info("AutomationManager a ser desligado. A parar o agendador e desubcrever eventos.")
        self._is_scheduler_running = False
        schedule.clear() # Limpa todas as tarefas agendadas
        if self._scheduler_thread and self._scheduler_thread.is_alive():
            self.logger.debug("Aguardando o thread do agendador terminar (pode demorar at√© 1 segundo).")
            self._scheduler_thread.join(timeout=1.5)
        
        # Desinscreve todos os event listeners
        for event_type, listeners in list(self._event_listeners.items()):
            for r_id, listener_func in listeners:
                self.event_manager.unsubscribe(event_type, listener_func)
            self._event_listeners[event_type].clear()
        
        self.event_manager.unsubscribe("GEM_SHUTDOWN", self._on_gem_shutdown)


# =============================================================================
# CLI Test
# =============================================================================

if __name__ == "__main__":
    import asyncio
    import json
    from collections import defaultdict
    import threading

    # Configure logging for standalone test
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger("TestAutomationManager")

    # --- Dummy Implementations for testing ---
    class DummyEventManager:
        def __init__(self, logger_instance):
            self.logger = logger_instance
            self._listeners = defaultdict(list)
        async def publish(self, event_type: str, data: Optional[Dict[str, Any]] = None) -> None:
            self.logger.info(f"Dummy EventManager: Publicado '{event_type}' com {data}")
            if event_type in self._listeners:
                for listener in self._listeners[event_type]:
                    # Run listeners in a non-blocking way
                    asyncio.create_task(listener(data))
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
            self.executed_commands: List[Tuple[str, Dict[str, Any]]] = []
        
        async def execute(self, command_name: str, **kwargs) -> Dict[str, Any]:
            self.logger.info(f"Dummy CommandExecutor: Executando '{command_name}' com kwargs={kwargs}")
            self.executed_commands.append((command_name, kwargs))
            # Simulate a real command execution
            if command_name == "tell_time":
                return {"success": True, "output": f"A hora atual √© {datetime.now().strftime('%H:%M')}", "error": None}
            elif command_name == "speak_text":
                return {"success": True, "output": f"Falei: {kwargs.get('text')}", "error": None}
            elif command_name == "system_status_check":
                return {"success": True, "output": "Status do sistema OK.", "error": None}
            elif command_name == "simulated_error_command":
                return {"success": False, "output": "", "error": "Erro simulado!"}
            return {"success": True, "output": f"Comando '{command_name}' executado com sucesso (simulado).", "error": None}

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

    async def run_automation_manager_tests():
        print("\n--- Iniciando Testes do AutomationManager ---")

        dummy_gem = DummyGEM(logger)
        automation_manager = AutomationManager(dummy_gem, logger)
        
        automation_manager.register_commands(dummy_gem.command_executor)

        await automation_manager.initialize()
        await asyncio.sleep(0.1) # Give scheduler thread a moment to start

        # --- Teste 1: Criar Rotina Di√°ria ---
        print("\n--- Teste 1: Criar Rotina Di√°ria ---")
        current_time = datetime.now()
        # Schedule for 10 seconds from now for testing purposes
        trigger_time_daily = (current_time + timedelta(seconds=10)).strftime("%H:%M")
        
        daily_actions_json = json.dumps([
            {"command_name": "tell_time"},
            {"command_name": "speak_text", "args": {"text": "Bom dia, √© hora de come√ßar o dia!"}}
        ])
        result_create_daily = await dummy_gem.command_executor.execute(
            "create_automation_routine",
            name="Rotina de Bom Dia",
            trigger_type="time_daily",
            trigger_value=trigger_time_daily,
            actions_json=daily_actions_json
        )
        print(result_create_daily["output"])
        assert result_create_daily["success"] is True
        assert "Rotina de automa√ß√£o 'Rotina de Bom Dia' criada com sucesso." in result_create_daily["output"]

        # --- Teste 2: Listar Rotinas ---
        print("\n--- Teste 2: Listar Rotinas ---")
        result_list = await dummy_gem.command_executor.execute("list_automation_routines")
        print(result_list["output"])
        assert result_list["success"] is True
        assert "Rotina de Bom Dia" in result_list["output"]

        print(f"\n--- Aguardando {11} segundos para a Rotina de Bom Dia (Trigger: {trigger_time_daily}) ---")
        await asyncio.sleep(11) # Wait for the daily routine to trigger

        # Verify that commands were executed by the dummy CommandExecutor
        assert any("tell_time" == cmd[0] for cmd in dummy_gem.command_executor.executed_commands)
        assert any("speak_text" == cmd[0] and "Bom dia, √© hora de come√ßar o dia!" in cmd[1].get("text", "") for cmd in dummy_gem.command_executor.executed_commands)
        assert any("A executar rotina: Rotina de Bom Dia" in n["message"] for n in dummy_gem.notification_manager.get_notification_history(limit=5))

        # --- Teste 3: Criar Rotina √önica ---
        print("\n--- Teste 3: Criar Rotina √önica ---")
        trigger_time_once = (current_time + timedelta(seconds=15)).strftime("%Y-%m-%d %H:%M") # 15s from now
        once_actions_json = json.dumps([
            {"command_name": "system_status_check"},
            {"command_name": "speak_text", "args": {"text": "Verifica√ß√£o √∫nica do sistema conclu√≠da."}}
        ])
        result_create_once = await dummy_gem.command_executor.execute(
            "create_automation_routine",
            name="Verifica√ß√£o √önica do Sistema",
            trigger_type="time_once",
            trigger_value=trigger_time_once,
            actions_json=once_actions_json
        )
        print(result_create_once["output"])
        assert result_create_once["success"] is True

        print(f"\n--- Aguardando {16} segundos para a Verifica√ß√£o √önica do Sistema (Trigger: {trigger_time_once}) ---")
        await asyncio.sleep(16) # Wait for the once routine to trigger

        assert any("system_status_check" == cmd[0] for cmd in dummy_gem.command_executor.executed_commands)
        assert any("speak_text" == cmd[0] and "Verifica√ß√£o √∫nica do sistema conclu√≠da." in cmd[1].get("text", "") for cmd in dummy_gem.command_executor.executed_commands)
        
        # Verify that the once routine is now disabled or removed from scheduler
        result_list_after_once = await dummy_gem.command_executor.execute("list_automation_routines")
        # Check if "Verifica√ß√£o √önica do Sistema" is listed and is_enabled is False
        assert "Verifica√ß√£o √önica do Sistema (Desativada)" in result_list_after_once["output"]

        # --- Teste 4: Criar Rotina Baseada em Evento ---
        print("\n--- Teste 4: Criar Rotina Baseada em Evento ---")
        event_actions_json = json.dumps([
            {"command_name": "speak_text", "args": {"text": "Um novo email foi recebido!"}}
        ])
        result_create_event = await dummy_gem.command_executor.execute(
            "create_automation_routine",
            name="Alerta de Novo Email",
            trigger_type="event_based",
            trigger_value="NEW_EMAIL_RECEIVED",
            actions_json=event_actions_json
        )
        print(result_create_event["output"])
        assert result_create_event["success"] is True

        # Simular o disparo do evento "NEW_EMAIL_RECEIVED"
        print("\n--- Teste 5: Disparar Evento para Rotina ---")
        await dummy_gem.event_manager.publish("NEW_EMAIL_RECEIVED", {"subject": "Teste de Evento"})
        await asyncio.sleep(0.5) # Give event listener time to process

        assert any("speak_text" == cmd[0] and "Um novo email foi recebido!" in cmd[1].get("text", "") for cmd in dummy_gem.command_executor.executed_commands)
        assert any("A executar rotina: Alerta de Novo Email" in n["message"] for n in dummy_gem.notification_manager.get_notification_history(limit=5))

        # --- Teste 6: Desativar e Ativar Rotina ---
        print("\n--- Teste 6: Desativar e Ativar Rotina ---")
        routine_id_daily = next(r.id for r in automation_manager._routines.values() if r.name == "Rotina de Bom Dia")
        
        result_disable = await dummy_gem.command_executor.execute("toggle_automation_routine", routine_id_prefix=routine_id_daily[:8], enable=False)
        print(result_disable["output"])
        assert result_disable["success"] is True
        assert "Rotina 'Rotina de Bom Dia' desativada com sucesso." in result_disable["output"]
        
        assert not automation_manager._routines[routine_id_daily].is_enabled
        # Verify it's no longer scheduled (hard to assert with schedule lib directly, but logging helps)

        result_enable = await dummy_gem.command_executor.execute("toggle_automation_routine", routine_id_prefix=routine_id_daily[:8], enable=True)
        print(result_enable["output"])
        assert result_enable["success"] is True
        assert "Rotina 'Rotina de Bom Dia' ativada com sucesso." in result_enable["output"]
        assert automation_manager._routines[routine_id_daily].is_enabled

        # --- Teste 7: Remover Rotina ---
        print("\n--- Teste 7: Remover Rotina ---")
        routine_id_event = next(r.id for r in automation_manager._routines.values() if r.name == "Alerta de Novo Email")
        
        result_delete = await dummy_gem.command_executor.execute("delete_automation_routine", routine_id_prefix=routine_id_event[:8])
        print(result_delete["output"])
        assert result_delete["success"] is True
        assert "Rotina 'Alerta de Novo Email' removida com sucesso." in result_delete["output"]
        
        assert routine_id_event not in automation_manager._routines # Verify deletion

        print("\n--- Testes do AutomationManager conclu√≠dos com sucesso. ---")
        automation_manager.shutdown()
        await asyncio.sleep(0.5) # Give shutdown tasks a moment
        assert not automation_manager._is_scheduler_running

    asyncio.run(run_automation_manager_tests())

