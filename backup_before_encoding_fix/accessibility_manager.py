#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
💎 GEM OS - Accessibility Manager (core/accessibility_manager.py)
Manages accessibility features and settings for GEM OS.

Responsibilities
----------------
- Centralize accessibility mode management (screen reader, high contrast, slow speech).
- Integrate with TTS to adjust speech rate and volume.
- Manage display settings like font size (for GUI if applicable).
- Provide alternative alerts for different needs.
- Expose accessibility features as tools for the LLM.
- Publish accessibility-related events.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional, Callable, Awaitable

from core.plugins import BasePlugin, CommandExecutor, GEMVoiceAssistant
from core.notification_manager import NotificationManager, NOTIFICATION_INFO

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
    def save(self) -> None:
        pass

# --- Accessibility Manager como um Plugin ---
class AccessibilityManager(BasePlugin):
    """
    Manages accessibility settings and features for GEM OS, acting as a plugin.
    """
    def __init__(self, gem_instance: GEMVoiceAssistant, logger: Optional[logging.Logger] = None):
        super().__init__(gem_instance, logger)
        self.logger.info("AccessibilityManager plugin inicializado.")
        
        self.event_manager: EventManager = gem_instance.event_manager
        self.notification_manager: NotificationManager = gem_instance.notification_manager
        self.tts_module: TTSModule = gem_instance.tts_module
        self.config_manager: ConfigManager = gem_instance.config_manager

        # Load initial accessibility settings from config
        self._screen_reader_mode: bool = self.config_manager.get_config().accessibility.screen_reader_mode
        self._slow_speech_rate: bool = self.config_manager.get_config().accessibility.slow_speech_rate
        self._high_contrast_mode: bool = self.config_manager.get_config().accessibility.high_contrast_mode
        self._font_size_multiplier: float = self.config_manager.get_config().accessibility.font_size_multiplier

        self.logger.info(f"Modos de acessibilidade iniciais: Leitor de Ecrã={self._screen_reader_mode}, Fala Lenta={self._slow_speech_rate}")

    async def initialize(self) -> None:
        """Performs any necessary setup for the accessibility manager."""
        self.event_manager.subscribe("GEM_SHUTDOWN", self._on_gem_shutdown)
        # Apply initial settings to other modules if needed (e.g., TTS speed)
        await self._apply_speech_rate_setting()
        self.logger.info("AccessibilityManager inicializado.")

    async def _on_gem_shutdown(self, event_data: Dict[str, Any]) -> None:
        """Handler for GEM_SHUTDOWN event."""
        self.logger.info("Recebido GEM_SHUTDOWN. AccessibilityManager a ser desligado.")
        self.shutdown()

    async def _apply_speech_rate_setting(self) -> None:
        """Applies the current speech rate setting to the TTS module."""
        if hasattr(self.tts_module, 'set_speech_rate'):
            # Assume TTSModule has a set_speech_rate method
            rate = 0.75 if self._slow_speech_rate else 1.0
            await self.tts_module.set_speech_rate(rate)
            self.logger.info(f"Velocidade da fala definida para {rate} (Lenta: {self._slow_speech_rate}).")
        else:
            self.logger.warning("TTSModule não tem método 'set_speech_rate'. Não é possível ajustar a velocidade da fala.")

    # --------------------------------------------------------------------- Commands

    async def _toggle_screen_reader_command(self) -> Dict[str, Any]:
        """Ativa ou desativa o modo de leitor de ecrã."""
        self._screen_reader_mode = not self._screen_reader_mode
        self.config_manager.get_config().accessibility.screen_reader_mode = self._screen_reader_mode
        self.config_manager.save()
        message = f"Modo de leitor de ecrã {'ativado' if self._screen_reader_mode else 'desativado'}."
        await self._speak_response(message)
        await self.notification_manager.add_notification(message, level=NOTIFICATION_INFO)
        await self.event_manager.publish("ACCESSIBILITY_MODE_CHANGED", {"mode": "screen_reader", "enabled": self._screen_reader_mode})
        self.logger.info(message)
        return {"success": True, "output": message, "error": None}

    async def _toggle_slow_speech_command(self) -> Dict[str, Any]:
        """Ativa ou desativa a taxa de fala lenta."""
        self._slow_speech_rate = not self._slow_speech_rate
        self.config_manager.get_config().accessibility.slow_speech_rate = self._slow_speech_rate
        self.config_manager.save()
        await self._apply_speech_rate_setting()
        message = f"Velocidade de fala {'lenta ativada' if self._slow_speech_rate else 'normal restaurada'}."
        await self._speak_response(message)
        await self.notification_manager.add_notification(message, level=NOTIFICATION_INFO)
        await self.event_manager.publish("ACCESSIBILITY_MODE_CHANGED", {"mode": "slow_speech", "enabled": self._slow_speech_rate})
        self.logger.info(message)
        return {"success": True, "output": message, "error": None}

    async def _set_font_size_multiplier_command(self, multiplier: float) -> Dict[str, Any]:
        """Define o multiplicador do tamanho da fonte (para interfaces gráficas)."""
        if not (0.5 <= multiplier <= 3.0): # Limit to a reasonable range
            message = "O multiplicador do tamanho da fonte deve estar entre 0.5 e 3.0."
            await self._speak_response(message)
            return {"success": False, "output": message, "error": "Invalid font size multiplier"}
        
        self._font_size_multiplier = multiplier
        self.config_manager.get_config().accessibility.font_size_multiplier = self._font_size_multiplier
        self.config_manager.save()
        message = f"Tamanho da fonte definido para {int(multiplier * 100)}%."
        await self._speak_response(message)
        await self.notification_manager.add_notification(message, level=NOTIFICATION_INFO)
        await self.event_manager.publish("ACCESSIBILITY_FONT_SIZE_CHANGED", {"multiplier": multiplier})
        self.logger.info(message)
        return {"success": True, "output": message, "error": None}

    async def _get_accessibility_status_command(self) -> Dict[str, Any]:
        """Reporta o status atual das configurações de acessibilidade."""
        message = (
            f"Status de Acessibilidade: "
            f"Leitor de Ecrã: {'Ativado' if self._screen_reader_mode else 'Desativado'}. "
            f"Fala Lenta: {'Ativada' if self._slow_speech_rate else 'Desativada'}. "
            f"Alto Contraste: {'Ativado' if self._high_contrast_mode else 'Desativado'}. "
            f"Tamanho da Fonte: {int(self._font_size_multiplier * 100)}%."
        )
        await self._speak_response(message)
        return {"success": True, "output": message, "error": None}

    # --------------------------------------------------------------------- Plugin Interface

    def register_commands(self, executor: CommandExecutor) -> None:
        """Registers accessibility commands with the CommandExecutor."""
        self.logger.info("A registar comandos do plugin AccessibilityManager...")
        executor.register_command("toggle_screen_reader", self._toggle_screen_reader_command)
        executor.register_command("toggle_slow_speech", self._toggle_slow_speech_command)
        executor.register_command("set_font_size_multiplier", self._set_font_size_multiplier_command)
        executor.register_command("get_accessibility_status", self._get_accessibility_status_command)
        # Mais comandos podem ser adicionados aqui para alto contraste, etc.
        self.logger.info("Comandos AccessibilityManager registados.")

    def get_tools_schema(self) -> List[Dict[str, Any]]:
        """
        Returns a list of tool definitions (schemas) for accessibility features.
        These schemas are exposed to the LLM for function calling.
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": "toggle_screen_reader",
                    "description": "Ativa ou desativa o modo de leitor de ecrã, que vocaliza todos os elementos da interface do usuário.",
                    "parameters": {"type": "object", "properties": {}, "required": []},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "toggle_slow_speech",
                    "description": "Ativa ou desativa a taxa de fala lenta para o GEM, tornando a vocalização mais fácil de seguir.",
                    "parameters": {"type": "object", "properties": {}, "required": []},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "set_font_size_multiplier",
                    "description": "Define um fator multiplicador para o tamanho da fonte da interface do usuário do GEM (para interfaces gráficas). O valor deve ser entre 0.5 (metade) e 3.0 (triplo).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "multiplier": {
                                "type": "number",
                                "format": "float",
                                "description": "O fator multiplicador do tamanho da fonte (ex: 1.0 para normal, 1.5 para 50% maior).",
                            }
                        },
                        "required": ["multiplier"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_accessibility_status",
                    "description": "Reporta o status atual de todas as configurações de acessibilidade do GEM, incluindo leitor de ecrã, fala lenta e tamanho da fonte.",
                    "parameters": {"type": "object", "properties": {}, "required": []},
                },
            },
            # Esquemas de ferramentas para alto contraste, etc., podem ser adicionados aqui.
        ]

    async def _speak_response(self, text: str) -> None:
        """Helper para vocalizar respostas através do módulo TTS principal do GEM."""
        if self.tts_module:
            await self.tts_module.speak(text)
        else:
            self.logger.warning(f"Módulo TTS não disponível para falar: '{text}'")

    def shutdown(self) -> None:
        """Performs any necessary cleanup."""
        self.logger.info("AccessibilityManager a ser desligado.")
        self.event_manager.unsubscribe("GEM_SHUTDOWN", self._on_gem_shutdown)


# =============================================================================
# CLI Test
# =============================================================================

if __name__ == "__main__":
    import asyncio
    
    # Configure logging for standalone test
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger("TestAccessibilityManager")

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
        async def add_notification(self, message: str, level: str = NOTIFICATION_INFO, vocalize: bool = True) -> None:
            self.logger.info(f"Dummy Notification: [{level.upper()}] {message} (Vocalize: {vocalize})")
            await asyncio.sleep(0.01)

    class DummyTTSModule:
        def __init__(self, logger_instance):
            self.logger = logger_instance
            self._speech_rate = 1.0 # Default
        async def speak(self, text: str) -> None:
            self.logger.info(f"Dummy TTS (Rate: {self._speech_rate}): A falar: '{text}'")
            await asyncio.sleep(0.01)
        async def set_speech_rate(self, rate: float) -> None:
            self._speech_rate = rate
            self.logger.info(f"Dummy TTS: Velocidade da fala definida para {rate}.")

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
                'accessibility': type('AccessibilityConfig', (), {
                    'screen_reader_mode': False,
                    'slow_speech_rate': False,
                    'high_contrast_mode': False,
                    'font_size_multiplier': 1.0
                })(),
                'general': type('GeneralConfig', (), {
                    'enable_audio_notifications': True # Para notificar
                })()
            })()
        def get_config(self) -> Any:
            return self.config
        def save(self) -> None:
            logger.info("Dummy ConfigManager: Configurações salvas (simulado).")


    class DummyGEM:
        def __init__(self, logger_instance: logging.Logger):
            self.logger = logger_instance
            self.event_manager = DummyEventManager(logger_instance)
            self.notification_manager = DummyNotificationManager(logger_instance)
            self.tts_module = DummyTTSModule(logger_instance)
            self.config_manager = DummyConfigManager()
            self.command_executor = DummyCommandExecutor(logger_instance)
            self.storage = type('DummyStorage', (), {})() # Not used directly

    async def run_accessibility_manager_tests():
        print("\n--- Iniciando Testes do AccessibilityManager ---")

        dummy_gem = DummyGEM(logger)
        accessibility_manager = AccessibilityManager(dummy_gem, logger)
        
        accessibility_manager.register_commands(dummy_gem.command_executor)

        await accessibility_manager.initialize()

        print("\n--- Teste 1: Alternar Leitor de Ecrã ---")
        result_toggle_sr = await dummy_gem.command_executor.execute("toggle_screen_reader")
        print(result_toggle_sr["output"])
        assert "Modo de leitor de ecrã ativado." in result_toggle_sr["output"]
        assert accessibility_manager._screen_reader_mode is True

        result_toggle_sr_again = await dummy_gem.command_executor.execute("toggle_screen_reader")
        print(result_toggle_sr_again["output"])
        assert "Modo de leitor de ecrã desativado." in result_toggle_sr_again["output"]
        assert accessibility_manager._screen_reader_mode is False

        print("\n--- Teste 2: Alternar Fala Lenta ---")
        result_toggle_ss = await dummy_gem.command_executor.execute("toggle_slow_speech")
        print(result_toggle_ss["output"])
        assert "Velocidade de fala lenta ativada." in result_toggle_ss["output"]
        assert accessibility_manager._slow_speech_rate is True
        assert dummy_gem.tts_module._speech_rate == 0.75

        result_toggle_ss_again = await dummy_gem.command_executor.execute("toggle_slow_speech")
        print(result_toggle_ss_again["output"])
        assert "Velocidade de fala normal restaurada." in result_toggle_ss_again["output"]
        assert accessibility_manager._slow_speech_rate is False
        assert dummy_gem.tts_module._speech_rate == 1.0

        print("\n--- Teste 3: Definir Multiplicador de Tamanho de Fonte ---")
        result_set_font = await dummy_gem.command_executor.execute("set_font_size_multiplier", multiplier=1.5)
        print(result_set_font["output"])
        assert "Tamanho da fonte definido para 150%." in result_set_font["output"]
        assert accessibility_manager._font_size_multiplier == 1.5

        result_set_font_invalid = await dummy_gem.command_executor.execute("set_font_size_multiplier", multiplier=4.0)
        print(result_set_font_invalid["output"])
        assert "O multiplicador do tamanho da fonte deve estar entre 0.5 e 3.0." in result_set_font_invalid["output"]
        assert accessibility_manager._font_size_multiplier == 1.5 # Should not have changed

        print("\n--- Teste 4: Obter Status de Acessibilidade ---")
        result_get_status = await dummy_gem.command_executor.execute("get_accessibility_status")
        print(result_get_status["output"])
        assert "Status de Acessibilidade:" in result_get_status["output"]
        assert "Leitor de Ecrã: Desativado." in result_get_status["output"]
        assert "Fala Lenta: Desativada." in result_get_status["output"]
        assert "Tamanho da Fonte: 150%." in result_get_status["output"]

        print("\n--- Testes do AccessibilityManager concluídos com sucesso. ---")
        accessibility_manager.shutdown()
        
    asyncio.run(run_accessibility_manager_tests())


