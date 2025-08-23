#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
💎 GEM OS - User Profile Manager (core/user_profile_manager.py)
Manages user preferences, personal information, and interaction history for a personalized experience.

Responsibilities
----------------
- Store and retrieve user preferences (e.g., units, timezone).
- Manage personal information (e.g., name, location, age - with consent).
- Maintain an interaction summary for personalization.
- Persist profile data using the Storage module.
- Expose profile management capabilities as tools for the LLM.
- Publish profile-related events.
- Integrate with NotificationManager for alerts.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable, Awaitable

from core.plugins import BasePlugin, CommandExecutor, GEMVoiceAssistant
from core.notification_manager import NotificationManager, NOTIFICATION_INFO, NOTIFICATION_SUCCESS, NOTIFICATION_WARNING

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

# --- Dataclass para Perfil do Utilizador ---
@dataclass
class UserProfile:
    user_name: str = "Utilizador GEM"
    preferred_language: str = "pt-BR"
    timezone: str = "America/Sao_Paulo" # Default timezone
    unit_system: str = "metric" # "metric" or "imperial"
    home_location: Optional[str] = None # E.g., "São Paulo, Brazil"
    age: Optional[int] = None
    last_interaction: Optional[datetime] = None
    interaction_count: int = 0
    # Adicionar outras preferências ou informações conforme necessário

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_name": self.user_name,
            "preferred_language": self.preferred_language,
            "timezone": self.timezone,
            "unit_system": self.unit_system,
            "home_location": self.home_location,
            "age": self.age,
            "last_interaction": self.last_interaction.isoformat() if self.last_interaction else None,
            "interaction_count": self.interaction_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> UserProfile:
        return cls(
            user_name=data.get("user_name", "Utilizador GEM"),
            preferred_language=data.get("preferred_language", "pt-BR"),
            timezone=data.get("timezone", "America/Sao_Paulo"),
            unit_system=data.get("unit_system", "metric"),
            home_location=data.get("home_location"),
            age=data.get("age"),
            last_interaction=datetime.fromisoformat(data["last_interaction"]) if data.get("last_interaction") else None,
            interaction_count=data.get("interaction_count", 0),
        )

# --- User Profile Manager como um Plugin ---
class UserProfileManager(BasePlugin):
    """
    Manages user profile data for GEM OS, acting as a plugin.
    """
    STORAGE_KEY_PROFILE = "user_profile_data"

    def __init__(self, gem_instance: GEMVoiceAssistant, logger: Optional[logging.Logger] = None):
        super().__init__(gem_instance, logger)
        self.logger.info("UserProfileManager plugin inicializado.")
        
        self.event_manager: EventManager = gem_instance.event_manager
        self.notification_manager: NotificationManager = gem_instance.notification_manager
        self.storage: Storage = gem_instance.storage
        self.tts_module: TTSModule = gem_instance.tts_module

        self._profile: UserProfile = UserProfile() # Default profile
        self._profile_loaded = asyncio.Event()

    async def initialize(self) -> None:
        """Loads the user profile from storage."""
        await self._load_profile_from_storage()
        self.event_manager.subscribe("GEM_SHUTDOWN", self._on_gem_shutdown)
        self.logger.info("UserProfileManager inicializado.")

    async def _on_gem_shutdown(self, event_data: Dict[str, Any]) -> None:
        """Handler for GEM_SHUTDOWN event."""
        self.logger.info("Recebido GEM_SHUTDOWN. UserProfileManager a ser desligado.")
        self.shutdown()

    async def _load_profile_from_storage(self) -> None:
        """Loads user profile data from persistent storage."""
        try:
            profile_data = await self.storage.get_setting(self.STORAGE_KEY_PROFILE)
            if profile_data:
                self._profile = UserProfile.from_dict(profile_data)
                self.logger.info("Perfil do utilizador carregado do armazenamento.")
            else:
                self.logger.info("Nenhum perfil do utilizador encontrado. A usar perfil padrão.")
        except Exception as e:
            self.logger.error(f"Falha ao carregar perfil do utilizador: {e}", exc_info=True)
        finally:
            self._profile_loaded.set() # Sinaliza que o perfil foi carregado

    async def _save_profile_to_storage(self) -> None:
        """Saves current user profile data to persistent storage."""
        try:
            await self.storage.set_setting(self.STORAGE_KEY_PROFILE, self._profile.to_dict())
            self.logger.debug("Perfil do utilizador salvo no armazenamento.")
        except Exception as e:
            self.logger.error(f"Falha ao salvar perfil do utilizador no armazenamento: {e}", exc_info=True)

    def get_profile(self) -> UserProfile:
        """Returns the current user profile object."""
        return self._profile

    async def update_last_interaction(self) -> None:
        """Updates the last interaction timestamp and count."""
        await self._profile_loaded.wait()
        self._profile.last_interaction = datetime.now()
        self._profile.interaction_count += 1
        await self._save_profile_to_storage()
        self.logger.debug("Última interação e contagem atualizadas.")

    # --------------------------------------------------------------------- Commands

    async def _set_user_name_command(self, name: str) -> Dict[str, Any]:
        """Define o nome do utilizador."""
        await self._profile_loaded.wait()
        old_name = self._profile.user_name
        self._profile.user_name = name
        await self._save_profile_to_storage()
        message = f"Nome do utilizador atualizado de '{old_name}' para '{name}'."
        await self._speak_response(message)
        await self.notification_manager.add_notification(message, level=NOTIFICATION_SUCCESS)
        await self.event_manager.publish("USER_PROFILE_UPDATED", {"field": "user_name", "value": name})
        self.logger.info(message)
        return {"success": True, "output": message, "error": None}

    async def _set_preferred_language_command(self, language_code: str) -> Dict[str, Any]:
        """Define o idioma preferencial do utilizador (ex: "en-US", "pt-BR")."""
        await self._profile_loaded.wait()
        old_lang = self._profile.preferred_language
        self._profile.preferred_language = language_code
        await self._save_profile_to_storage()
        message = f"Idioma preferencial atualizado de '{old_lang}' para '{language_code}'."
        await self._speak_response(message)
        await self.notification_manager.add_notification(message, level=NOTIFICATION_SUCCESS)
        await self.event_manager.publish("USER_PROFILE_UPDATED", {"field": "preferred_language", "value": language_code})
        self.logger.info(message)
        return {"success": True, "output": message, "error": None}
    
    async def _set_home_location_command(self, location: str) -> Dict[str, Any]:
        """Define a localização de residência do utilizador (ex: "São Paulo, Brazil")."""
        await self._profile_loaded.wait()
        old_location = self._profile.home_location
        self._profile.home_location = location
        await self._save_profile_to_storage()
        message = f"Localização de residência atualizada de '{old_location}' para '{location}'."
        await self._speak_response(message)
        await self.notification_manager.add_notification(message, level=NOTIFICATION_SUCCESS)
        await self.event_manager.publish("USER_PROFILE_UPDATED", {"field": "home_location", "value": location})
        self.logger.info(message)
        return {"success": True, "output": message, "error": None}

    async def _get_user_profile_command(self) -> Dict[str, Any]:
        """Recupera e reporta todas as informações do perfil do utilizador."""
        await self._profile_loaded.wait()
        profile_data = self._profile.to_dict()
        
        output_lines = ["Informações do seu perfil:"]
        for key, value in profile_data.items():
            if value is not None:
                output_lines.append(f"- {key.replace('_', ' ').capitalize()}: {value}")
        
        message = "\n".join(output_lines)
        await self._speak_response("As suas informações de perfil foram listadas. Verifique o ecrã para os detalhes.")
        await self.notification_manager.add_notification("Informações de perfil exibidas.", level=NOTIFICATION_INFO)
        await self.event_manager.publish("USER_PROFILE_REQUESTED", profile_data)
        return {"success": True, "output": message, "error": None}

    # --------------------------------------------------------------------- Plugin Interface

    def register_commands(self, executor: CommandExecutor) -> None:
        """Registers user profile management commands with the CommandExecutor."""
        self.logger.info("A registar comandos do plugin UserProfileManager...")
        executor.register_command("set_user_name", self._set_user_name_command)
        executor.register_command("set_preferred_language", self._set_preferred_language_command)
        executor.register_command("set_home_location", self._set_home_location_command)
        executor.register_command("get_user_profile", self._get_user_profile_command)
        self.logger.info("Comandos UserProfileManager registados.")

    def get_tools_schema(self) -> List[Dict[str, Any]]:
        """
        Returns a list of tool definitions (schemas) for user profile features.
        These schemas are exposed to the LLM for function calling.
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": "set_user_name",
                    "description": "Define ou atualiza o nome preferencial do usuário para o GEM.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "O novo nome que o usuário gostaria de ser chamado.",
                            },
                        },
                        "required": ["name"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "set_preferred_language",
                    "description": "Define o idioma preferencial do usuário para as interações com o GEM. Use códigos de idioma como 'pt-BR' para Português (Brasil) ou 'en-US' para Inglês (EUA).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "language_code": {
                                "type": "string",
                                "description": "O código do idioma preferencial (ex: 'pt-BR', 'en-US').",
                            },
                        },
                        "required": ["language_code"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "set_home_location",
                    "description": "Define a localização de residência do usuário. Isso pode ser usado para informações baseadas em localização (clima, notícias locais).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {
                                "type": "string",
                                "description": "O nome da cidade e país (ex: 'São Paulo, Brasil').",
                            },
                        },
                        "required": ["location"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_user_profile",
                    "description": "Recupera e vocaliza todas as informações do perfil do usuário, incluindo nome, idioma, localização, etc.",
                    "parameters": {"type": "object", "properties": {}, "required": []},
                },
            },
            # Mais ferramentas para atualizar outros campos do perfil (idade, fuso horário, etc.) podem ser adicionadas.
        ]

    async def _speak_response(self, text: str) -> None:
        """Helper para vocalizar respostas através do módulo TTS principal do GEM."""
        if self.tts_module:
            await self.tts_module.speak(text)
        else:
            self.logger.warning(f"Módulo TTS não disponível para falar: '{text}'")

    def shutdown(self) -> None:
        """Performs any necessary cleanup."""
        self.logger.info("UserProfileManager a ser desligado.")
        self.event_manager.unsubscribe("GEM_SHUTDOWN", self._on_gem_shutdown)


# =============================================================================
# CLI Test
# =============================================================================

if __name__ == "__main__":
    import asyncio
    
    # Configure logging for standalone test
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger("TestUserProfileManager")

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

    async def run_user_profile_manager_tests():
        print("\n--- Iniciando Testes do UserProfileManager ---")

        dummy_gem = DummyGEM(logger)
        user_profile_manager = UserProfileManager(dummy_gem, logger)
        
        user_profile_manager.register_commands(dummy_gem.command_executor)

        await user_profile_manager.initialize()

        # --- Teste 1: Obter Perfil Inicial (Padrão) ---
        print("\n--- Teste 1: Obter Perfil Inicial (Padrão) ---")
        result_get_initial = await dummy_gem.command_executor.execute("get_user_profile")
        print(result_get_initial["output"])
        assert result_get_initial["success"] is True
        assert "Utilizador GEM" in result_get_initial["output"]
        assert "pt-BR" in result_get_initial["output"]

        # --- Teste 2: Definir Nome do Utilizador ---
        print("\n--- Teste 2: Definir Nome do Utilizador ---")
        result_set_name = await dummy_gem.command_executor.execute("set_user_name", name="João Silva")
        print(result_set_name["output"])
        assert result_set_name["success"] is True
        assert "Nome do utilizador atualizado de 'Utilizador GEM' para 'João Silva'." in result_set_name["output"]
        assert user_profile_manager.get_profile().user_name == "João Silva"

        # --- Teste 3: Definir Idioma Preferencial ---
        print("\n--- Teste 3: Definir Idioma Preferencial ---")
        result_set_lang = await dummy_gem.command_executor.execute("set_preferred_language", language_code="en-US")
        print(result_set_lang["output"])
        assert result_set_lang["success"] is True
        assert "Idioma preferencial atualizado de 'pt-BR' para 'en-US'." in result_set_lang["output"]
        assert user_profile_manager.get_profile().preferred_language == "en-US"
        
        # --- Teste 4: Definir Localização de Residência ---
        print("\n--- Teste 4: Definir Localização de Residência ---")
        result_set_location = await dummy_gem.command_executor.execute("set_home_location", location="Rio de Janeiro, Brasil")
        print(result_set_location["output"])
        assert result_set_location["success"] is True
        assert "Localização de residência atualizada de 'None' para 'Rio de Janeiro, Brasil'." in result_set_location["output"]
        assert user_profile_manager.get_profile().home_location == "Rio de Janeiro, Brasil"

        # --- Teste 5: Obter Perfil Atualizado ---
        print("\n--- Teste 5: Obter Perfil Atualizado ---")
        result_get_updated = await dummy_gem.command_executor.execute("get_user_profile")
        print(result_get_updated["output"])
        assert result_get_updated["success"] is True
        assert "João Silva" in result_get_updated["output"]
        assert "en-US" in result_get_updated["output"]
        assert "Rio de Janeiro, Brasil" in result_get_updated["output"]
        
        # Simular atualização de interação
        await user_profile_manager.update_last_interaction()
        assert user_profile_manager.get_profile().interaction_count == 1
        assert user_profile_manager.get_profile().last_interaction is not None

        print("\n--- Testes do UserProfileManager concluídos com sucesso. ---")
        user_profile_manager.shutdown()
        
    asyncio.run(run_user_profile_manager_tests())

