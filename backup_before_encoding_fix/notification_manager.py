#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
💎 GEM OS - Notification Manager (core/notification_manager.py)
Manages and dispatches various types of notifications to the user.

Responsibilities
----------------
- Handle incoming notification requests.
- Integrate with TTS module to vocalize notifications.
- Potentially integrate with a display module for visual alerts (future).
- Maintain a log/history of notifications.
- Publish notification-related events.
"""

from __future__ import annotations

import asyncio
import logging
from collections import deque
from datetime import datetime
from typing import Any, Dict, List, Optional, Deque

# Forward declarations for type hinting, actual objects passed at runtime
class EventManager:
    async def publish(self, event_type: str, data: Optional[Dict[str, Any]] = None) -> None:
        pass

class TTSModule:
    async def speak(self, text: str) -> None:
        pass

class GEMVoiceAssistant:
    event_manager: EventManager
    tts_module: TTSModule
    logger: logging.Logger
    config_manager: Any # Assumindo que tem um método get_config()

# Notification levels
NOTIFICATION_INFO = "info"
NOTIFICATION_WARNING = "warning"
NOTIFICATION_ERROR = "error"
NOTIFICATION_SUCCESS = "success"

@dataclass
class Notification:
    """Represents a single notification."""
    timestamp: datetime
    message: str
    level: str = NOTIFICATION_INFO
    spoken: bool = False
    displayed: bool = False

class NotificationManager:
    """
    Manages the creation, dispatch, and history of system notifications.
    """
    def __init__(self, gem_instance: GEMVoiceAssistant, logger: Optional[logging.Logger] = None):
        self.gem = gem_instance
        self.logger = logger or logging.getLogger(__name__)
        
        self.event_manager: EventManager = gem_instance.event_manager
        self.tts_module: TTSModule = gem_instance.tts_module
        self.config_manager = gem_instance.config_manager

        self._notification_queue: Deque[Notification] = deque()
        self._notification_history: Deque[Notification] = deque(maxlen=self.config_manager.get_config().general.max_notification_history)
        self._processing_task: Optional[asyncio.Task] = None
        self._is_running: bool = False

        self.logger.info("NotificationManager inicializado.")

        # Subscribe to internal events to trigger notifications
        self.event_manager.subscribe("SYSTEM_ALERT", self._on_system_alert_event)
        self.event_manager.subscribe("TASK_COMPLETED", self._on_task_completed_event)
        self.event_manager.subscribe("ERROR_OCCURRED", self._on_error_occurred_event)
        # Add more event subscriptions as needed

    async def initialize(self) -> None:
        """Starts the background task for processing notifications."""
        if not self._is_running:
            self._is_running = True
            self._processing_task = asyncio.create_task(self._process_notifications())
            self.logger.info("NotificationManager iniciado.")

    async def _process_notifications(self) -> None:
        """Background task to process and dispatch notifications from the queue."""
        self.logger.debug("Loop de processamento de notificações iniciado.")
        while self._is_running:
            try:
                if self._notification_queue:
                    notification = self._notification_queue.popleft()
                    await self._dispatch_notification(notification)
                else:
                    await asyncio.sleep(0.1) # Sleep briefly if no notifications
            except asyncio.CancelledError:
                self.logger.info("Tarefa de processamento de notificações cancelada.")
                break
            except Exception as e:
                self.logger.error(f"Erro no loop de processamento de notificações: {e}", exc_info=True)
                await asyncio.sleep(1.0) # Prevent busy-loop on error
        self.logger.debug("Loop de processamento de notificações terminado.")

    async def add_notification(self, message: str, level: str = NOTIFICATION_INFO, vocalize: bool = True) -> None:
        """
        Adds a new notification to the queue for processing.
        
        Args:
            message: The content of the notification.
            level: The severity level (info, warning, error, success).
            vocalize: Whether the notification should be spoken aloud by TTS.
        """
        new_notification = Notification(
            timestamp=datetime.now(),
            message=message,
            level=level,
            spoken=False # Will be set to True after speaking
        )
        self._notification_queue.append(new_notification)
        self._notification_history.append(new_notification) # Add to history immediately
        self.logger.debug(f"Notificação adicionada à fila ({level}): {message[:100]}...")
        await self.event_manager.publish("NOTIFICATION_ADDED", {"notification": new_notification})

    async def _dispatch_notification(self, notification: Notification) -> None:
        """Dispatches a notification (vocalizes, logs, potentially displays)."""
        self.logger.log(self._get_log_level(notification.level), f"[{notification.level.upper()}] {notification.message}")

        if notification.spoken: # If already marked as spoken (e.g., in _on_event handlers)
            pass
        elif self.config_manager.get_config().general.enable_audio_notifications: # Global config for audio notifications
            if notification.level == NOTIFICATION_ERROR:
                await self.tts_module.speak(f"Erro: {notification.message}")
            elif notification.level == NOTIFICATION_WARNING:
                await self.tts_module.speak(f"Atenção: {notification.message}")
            else:
                await self.tts_module.speak(notification.message)
            notification.spoken = True
        
        # Future: Integrate with a display system for visual notifications
        # if self.gem.display_module and self.config_manager.get_config().general.enable_visual_notifications:
        #    await self.gem.display_module.show_notification(notification)
        #    notification.displayed = True

        await self.event_manager.publish("NOTIFICATION_DISPATCHED", {"notification": notification})

    def get_notification_history(self, limit: int = 10) -> List[Notification]:
        """
        Returns a list of recent notifications from history.
        The most recent notifications are at the end of the list.
        """
        return list(self._notification_history)[-limit:]

    def _get_log_level(self, level: str) -> int:
        """Maps notification level strings to logging levels."""
        return {
            NOTIFICATION_INFO: logging.INFO,
            NOTIFICATION_WARNING: logging.WARNING,
            NOTIFICATION_ERROR: logging.ERROR,
            NOTIFICATION_SUCCESS: logging.INFO, # Success also as INFO
        }.get(level, logging.INFO)

    # ---------------------------------------------------------------- Event Handlers

    async def _on_system_alert_event(self, event_data: Dict[str, Any]) -> None:
        """Handler for SYSTEM_ALERT events."""
        message = event_data.get("message", "Alerta do sistema desconhecido.")
        level = event_data.get("level", NOTIFICATION_WARNING)
        self.logger.warning(f"Recebido SYSTEM_ALERT: {message} ({level})")
        await self.add_notification(f"Alerta do sistema: {message}", level=level, vocalize=True)

    async def _on_task_completed_event(self, event_data: Dict[str, Any]) -> None:
        """Handler for TASK_COMPLETED events."""
        task_name = event_data.get("task_name", "Tarefa")
        result = event_data.get("result", "concluída")
        self.logger.info(f"Recebido TASK_COMPLETED: {task_name} - {result}")
        await self.add_notification(f"Tarefa '{task_name}' {result}.", level=NOTIFICATION_SUCCESS, vocalize=True)

    async def _on_error_occurred_event(self, event_data: Dict[str, Any]) -> None:
        """Handler for ERROR_OCCURRED events."""
        error_message = event_data.get("message", "Ocorreu um erro desconhecido.")
        source = event_data.get("source", "sistema")
        self.logger.error(f"Recebido ERROR_OCCURRED de '{source}': {error_message}")
        await self.add_notification(f"Erro no {source}: {error_message}", level=NOTIFICATION_ERROR, vocalize=True)

    def shutdown(self) -> None:
        """Stops the notification processing task and performs cleanup."""
        self.logger.info("NotificationManager a ser desligado.")
        self._is_running = False
        if self._processing_task:
            self._processing_task.cancel()
            self.logger.debug("Tarefa de processamento de notificações cancelada.")
        self._notification_queue.clear()
        self.event_manager.unsubscribe("SYSTEM_ALERT", self._on_system_alert_event)
        self.event_manager.unsubscribe("TASK_COMPLETED", self._on_task_completed_event)
        self.event_manager.unsubscribe("ERROR_OCCURRED", self._on_error_occurred_event)


# =============================================================================
# CLI Test
# =============================================================================

if __name__ == "__main__":
    import asyncio
    
    # Configure logging for standalone test
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger("TestNotificationManager")

    # --- Dummy Implementations for testing ---
    class DummyEventManager:
        def __init__(self, logger):
            self.logger = logger
            self._listeners = defaultdict(list)
        async def publish(self, event_type: str, data: Optional[Dict[str, Any]] = None) -> None:
            self.logger.info(f"Dummy EventManager: Publicado '{event_type}' com {data}")
            if event_type in self._listeners:
                for listener in self._listeners[event_type]:
                    asyncio.create_task(listener(data))
        def subscribe(self, event_type: str, listener: Callable) -> None:
            self.logger.debug(f"Dummy EventManager: Subscrito '{listener.__name__}' para '{event_type}'")
            self._listeners[event_type].append(listener)
        def unsubscribe(self, event_type: str, listener: Callable) -> None:
            if event_type in self._listeners and listener in self._listeners[event_type]:
                self._listeners[event_type].remove(listener)
                self.logger.debug(f"Dummy EventManager: Desubscrito '{listener.__name__}' de '{event_type}'")

    class DummyTTSModule:
        def __init__(self, logger):
            self.logger = logger
        async def speak(self, text: str) -> None:
            self.logger.info(f"Dummy TTS: A falar: '{text}'")
            await asyncio.sleep(0.01) # Simulate speaking time

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
            self.tts_module = DummyTTSModule(logger_instance)
            self.config_manager = DummyConfigManager()
            # Outros módulos podem ser adicionados aqui se o NotificationManager precisar deles

    async def run_notification_manager_tests():
        print("\n--- Iniciando Testes do NotificationManager ---")

        dummy_gem = DummyGEM(logger)
        notification_manager = NotificationManager(dummy_gem, logger)
        await notification_manager.initialize()

        print("\n--- Teste 1: Adicionar Notificações Manuais ---")
        await notification_manager.add_notification("Bem-vindo ao GEM OS!", level=NOTIFICATION_INFO)
        await notification_manager.add_notification("Atualização disponível.", level=NOTIFICATION_INFO, vocalize=False)
        await notification_manager.add_notification("Uso de CPU elevado.", level=NOTIFICATION_WARNING)
        await notification_manager.add_notification("Erro crítico no subsistema X.", level=NOTIFICATION_ERROR)
        await notification_manager.add_notification("Tarefa de backup concluída com sucesso.", level=NOTIFICATION_SUCCESS)
        
        await asyncio.sleep(0.5) # Dá tempo para o processamento da fila

        print("\n--- Teste 2: Verificar Histórico de Notificações ---")
        history = notification_manager.get_notification_history(limit=3)
        print(f"Histórico (últimas 3):")
        for n in history:
            print(f"  [{n.timestamp.strftime('%H:%M:%S')}] {n.level.upper()}: {n.message} (Falado: {n.spoken})")
        assert len(history) == 3
        assert history[0].level == NOTIFICATION_ERROR # Devido ao maxlen=5, as mais antigas saem
        assert history[2].message == "Tarefa de backup concluída com sucesso."

        print("\n--- Teste 3: Disparar Notificações via Eventos ---")
        await dummy_gem.event_manager.publish("SYSTEM_ALERT", {"message": "Bateria fraca!", "level": NOTIFICATION_WARNING})
        await dummy_gem.event_manager.publish("TASK_COMPLETED", {"task_name": "Inicialização", "result": "bem-sucedida"})
        await dummy_gem.event_manager.publish("ERROR_OCCURRED", {"message": "Falha na conexão de rede.", "source": "NetworkModule"})
        
        await asyncio.sleep(0.5) # Dá tempo para os eventos serem processados e as notificações serem adicionadas/despachadas

        history_after_events = notification_manager.get_notification_history(limit=5)
        print("\nHistórico após eventos:")
        for n in history_after_events:
            print(f"  [{n.timestamp.strftime('%H:%M:%S')}] {n.level.upper()}: {n.message} (Falado: {n.spoken})")
        assert len(history_after_events) == 5 # Garante que o histórico se expande até o maxlen

        print("\n--- Testes do NotificationManager concluídos com sucesso. ---")
        notification_manager.shutdown()
        await asyncio.sleep(0.1) # Give shutdown task a moment
        assert not notification_manager._is_running
        assert notification_manager._processing_task.done()

    asyncio.run(run_notification_manager_tests())


