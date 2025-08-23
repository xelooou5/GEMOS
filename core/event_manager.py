#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ğŸ’� GEM OS - Event Manager (core/event_manager.py)
Manages a publish-subscribe event system for inter-module communication.

Responsibilities
----------------
- Provide a central hub for event registration and emission.
- Enable asynchronous event handling.
- Decouple modules by allowing indirect communication.
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

# Type alias for event listeners
EventListener = Callable[[Dict[str, Any]], Awaitable[None]]

class EventManager:
    """
    Manages a publish-subscribe system for asynchronous event handling
    across different GEM OS modules and plugins.
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        # Dictionary to store event type -> set of listeners
        self._listeners: Dict[str, Set[EventListener]] = defaultdict(set)
        self.logger.info("EventManager inicializado.")

    def subscribe(self, event_type: str, listener: EventListener) -> None:
        """
        Registers an asynchronous listener function for a specific event type.
        
        Args:
            event_type: The string identifier for the event (e.g., "STT_TRANSCRIBED", "COMMAND_EXECUTED").
            listener: An async callable that will be invoked when the event is published.
                      It should accept a single argument: a dictionary of event data.
        """
        self._listeners[event_type].add(listener)
        self.logger.debug(f"Subscrito para '{event_type}': {listener.__name__}")

    def unsubscribe(self, event_type: str, listener: EventListener) -> None:
        """
        Unregisters a listener function from a specific event type.
        
        Args:
            event_type: The string identifier for the event.
            listener: The async callable to unregister.
        """
        if listener in self._listeners[event_type]:
            self._listeners[event_type].remove(listener)
            self.logger.debug(f"Desubscrito de '{event_type}': {listener.__name__}")
        else:
            self.logger.warning(f"Tentativa de desubcrever um listener nÃ£o registado para '{event_type}': {listener.__name__}")

    async def publish(self, event_type: str, data: Optional[Dict[str, Any]] = None) -> None:
        """
        Publishes an event, notifying all registered listeners for that event type.
        Listeners are invoked concurrently without blocking the publisher.
        
        Args:
            event_type: The string identifier for the event.
            data: An optional dictionary containing data relevant to the event.
        """
        if data is None:
            data = {}
        
        self.logger.info(f"Publicando evento '{event_type}' com dados: {data}")
        
        if event_type in self._listeners:
            tasks = []
            for listener in list(self._listeners[event_type]): # Use list to avoid issues if a listener unsubscribes itself
                try:
                    tasks.append(listener(data))
                except Exception as e:
                    self.logger.error(f"Erro ao preparar listener '{listener.__name__}' para evento '{event_type}': {e}", exc_info=True)
            
            if tasks:
                # Run listeners concurrently as a group without waiting for them to complete
                # This ensures the publisher doesn't block, but also allows listeners to run
                asyncio.create_task(asyncio.gather(*tasks, return_exceptions=True))
                self.logger.debug(f"Despachadas {len(tasks)} tarefas para o evento '{event_type}'.")
            else:
                self.logger.debug(f"Nenhum listener para o evento '{event_type}'.")
        else:
            self.logger.debug(f"Nenhum listener para o evento '{event_type}'.")

    def shutdown(self) -> None:
        """Clears all registered listeners and performs any necessary cleanup."""
        self.logger.info("EventManager a ser desligado. A limpar todos os listeners.")
        self._listeners.clear()

# =============================================================================
# CLI Test
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger("TestEventManager")

    async def listener_a(event_data: Dict[str, Any]) -> None:
        logger.info(f"Listener A recebeu: {event_data.get('message', 'Nenhuma mensagem')}")
        await asyncio.sleep(0.1) # Simulate some async work
        logger.debug("Listener A terminou.")

    async def listener_b(event_data: Dict[str, Any]) -> None:
        logger.info(f"Listener B recebeu: {event_data.get('count', 0)} itens.")
        await asyncio.sleep(0.2) # Simulate more async work
        logger.debug("Listener B terminou.")

    async def listener_c_unsubscribes(event_data: Dict[str, Any]) -> None:
        logger.info(f"Listener C recebeu: {event_data.get('status', 'desconhecido')}. Vou desubcrever-me!")
        # Simula um listener que se desubcreve a si prÃ³prio
        global event_manager # Aceder Ã  instÃ¢ncia global para desubcrever
        if event_manager:
            event_manager.unsubscribe("status_update", listener_c_unsubscribes)
        await asyncio.sleep(0.05)
        logger.debug("Listener C terminou e desubcreveu-se.")

    async def run_event_manager_tests():
        print("\n--- Iniciando Testes do EventManager ---")
        
        global event_manager # Para permitir que listener_c_unsubscribes aceda a ele
        event_manager = EventManager(logger)

        print("\n--- Teste 1: Subcrever e Publicar eventos bÃ¡sicos ---")
        event_manager.subscribe("user_input", listener_a)
        event_manager.subscribe("data_ready", listener_b)

        await event_manager.publish("user_input", {"message": "OlÃ¡ GEM!"})
        await event_manager.publish("data_ready", {"count": 10, "source": "API"})
        
        # Give some time for async tasks to run
        await asyncio.sleep(0.5) 

        print("\n--- Teste 2: Publicar evento sem listeners ---")
        await event_manager.publish("non_existent_event", {"info": "Este nÃ£o deve ser ouvido por ninguÃ©m."})
        await asyncio.sleep(0.1)

        print("\n--- Teste 3: Listener que se desubcreve ---")
        event_manager.subscribe("status_update", listener_c_unsubscribes)
        await event_manager.publish("status_update", {"status": "iniciado"})
        await asyncio.sleep(0.2)
        # Publicar novamente para ver se o Listener C ainda Ã© invocado
        print("\n--- Publicando 'status_update' novamente apÃ³s desubscriÃ§Ã£o do Listener C ---")
        await event_manager.publish("status_update", {"status": "continuando"})
        await asyncio.sleep(0.2)
        
        # Verify if listener_c_unsubscribes is no longer in the set
        assert listener_c_unsubscribes not in event_manager._listeners["status_update"]
        print("âœ… Listener C verificado como desubscrito.")

        print("\n--- Teste 4: Desligamento do EventManager ---")
        event_manager.shutdown()
        # ApÃ³s o desligamento, a publicaÃ§Ã£o nÃ£o deve invocar nada
        await event_manager.publish("user_input", {"message": "Isto nÃ£o deve ser ouvido apÃ³s o desligamento."})
        await asyncio.sleep(0.1)
        assert not event_manager._listeners # Verifica se os listeners foram limpos
        print("âœ… EventManager desligado e listeners limpos.")

        print("\n--- Testes do EventManager concluÃ­dos com sucesso. ---")

    asyncio.run(run_event_manager_tests())


