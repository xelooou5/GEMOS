#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
üíé GEM OS - Knowledge Manager (core/knowledge_manager.py)
Manages user-specific knowledge, facts, and personalized information.

Responsibilities
----------------
- Store and retrieve user-defined facts/knowledge.
- Enable the LLM to query and utilize this knowledge.
- Add, update, and remove knowledge entries.
- Persist knowledge data using the Storage module.
- Expose knowledge management capabilities as tools for the LLM.
- Publish knowledge-related events.
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

# --- Dataclass para Entrada de Conhecimento ---
@dataclass
class KnowledgeEntry:
    key: str # The fact/knowledge name (e.g., "my_favorite_color", "my_birthday")
    value: str # The actual knowledge (e.g., "blue", "1990-05-15")
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = "user_input" # "user_input", "system_learned"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> KnowledgeEntry:
        return cls(
            key=data["key"],
            value=data["value"],
            timestamp=datetime.fromisoformat(data["timestamp"]) if data.get("timestamp") else datetime.now(),
            source=data.get("source", "user_input"),
        )

# --- Knowledge Manager como um Plugin ---
class KnowledgeManager(BasePlugin):
    """
    Manages user-specific knowledge and facts for GEM OS, acting as a plugin.
    """
    STORAGE_KEY_KNOWLEDGE = "gem_user_knowledge"

    def __init__(self, gem_instance: GEMVoiceAssistant, logger: Optional[logging.Logger] = None):
        super().__init__(gem_instance, logger)
        self.logger.info("KnowledgeManager plugin inicializado.")
        
        self.event_manager: EventManager = gem_instance.event_manager
        self.notification_manager: NotificationManager = gem_instance.notification_manager
        self.storage: Storage = gem_instance.storage
        self.tts_module: TTSModule = gem_instance.tts_module

        self._knowledge: Dict[str, KnowledgeEntry] = {} # {key: KnowledgeEntry_object}
        self._knowledge_loaded = asyncio.Event()

    async def initialize(self) -> None:
        """Loads knowledge entries from storage."""
        await self._load_knowledge_from_storage()
        self.event_manager.subscribe("GEM_SHUTDOWN", self._on_gem_shutdown)
        self.logger.info("KnowledgeManager inicializado.")

    async def _on_gem_shutdown(self, event_data: Dict[str, Any]) -> None:
        """Handler for GEM_SHUTDOWN event."""
        self.logger.info("Recebido GEM_SHUTDOWN. KnowledgeManager a ser desligado.")
        self.shutdown()

    async def _load_knowledge_from_storage(self) -> None:
        """Loads knowledge entries from persistent storage."""
        try:
            knowledge_data_list = await self.storage.get_setting(self.STORAGE_KEY_KNOWLEDGE, [])
            for entry_dict in knowledge_data_list:
                try:
                    entry = KnowledgeEntry.from_dict(entry_dict)
                    self._knowledge[entry.key] = entry
                except Exception as e:
                    self.logger.error(f"Erro ao carregar entrada de conhecimento do armazenamento: {e} - Dados: {entry_dict}", exc_info=True)
            self.logger.info(f"Carregadas {len(self._knowledge)} entradas de conhecimento do armazenamento.")
        except Exception as e:
            self.logger.error(f"Falha ao carregar conhecimento do armazenamento: {e}", exc_info=True)
        finally:
            self._knowledge_loaded.set() # Sinaliza que o conhecimento foi carregado

    async def _save_knowledge_to_storage(self) -> None:
        """Saves current knowledge entries to persistent storage."""
        try:
            knowledge_data_list = [entry.to_dict() for entry in self._knowledge.values()]
            await self.storage.set_setting(self.STORAGE_KEY_KNOWLEDGE, knowledge_data_list)
            self.logger.debug(f"Salvas {len(self._knowledge)} entradas de conhecimento para o armazenamento.")
        except Exception as e:
            self.logger.error(f"Falha ao salvar conhecimento no armazenamento: {e}", exc_info=True)

    # --------------------------------------------------------------------- Commands

    async def _add_knowledge_command(self, key: str, value: str, source: str = "user_input") -> Dict[str, Any]:
        """
        Adiciona ou atualiza uma entrada de conhecimento.
        
        Args:
            key: A chave ou nome do conhecimento (ex: "meu_endere√ßo", "minha_comida_favorita").
            value: O valor ou conte√∫do do conhecimento.
            source: A origem do conhecimento (ex: "user_input", "system_learned").
        """
        await self._knowledge_loaded.wait()

        new_entry = KnowledgeEntry(key=key, value=value, source=source, timestamp=datetime.now())
        self._knowledge[key] = new_entry
        await self._save_knowledge_to_storage()

        message = f"Conhecimento '{key}' adicionado/atualizado com sucesso."
        await self._speak_response(message)
        await self.notification_manager.add_notification(message, level=NOTIFICATION_SUCCESS)
        await self.event_manager.publish("KNOWLEDGE_ADDED_UPDATED", {"key": key, "value": value})
        self.logger.info(message)
        return {"success": True, "output": message, "error": None}

    async def _get_knowledge_command(self, key: str) -> Dict[str, Any]:
        """
        Recupera o valor de uma entrada de conhecimento pela sua chave.
        """
        await self._knowledge_loaded.wait()

        entry = self._knowledge.get(key)
        if not entry:
            message = f"Conhecimento '{key}' n√£o encontrado."
            await self._speak_response(message)
            return {"success": False, "output": "", "error": message}
        
        message = f"O conhecimento para '{key}' √©: {entry.value}"
        await self._speak_response(message)
        await self.notification_manager.add_notification(f"Conhecimento para '{key}' recuperado.", level=NOTIFICATION_INFO)
        await self.event_manager.publish("KNOWLEDGE_RETRIEVED", {"key": key, "value": entry.value})
        self.logger.info(message)
        return {"success": True, "output": entry.value, "error": None}

    async def _delete_knowledge_command(self, key: str) -> Dict[str, Any]:
        """
        Remove uma entrada de conhecimento pela sua chave.
        """
        await self._knowledge_loaded.wait()

        if key not in self._knowledge:
            message = f"Conhecimento '{key}' n√£o encontrado para remo√ß√£o."
            await self._speak_response(message)
            return {"success": False, "output": "", "error": message}

        del self._knowledge[key]
        await self._save_knowledge_to_storage()

        message = f"Conhecimento '{key}' removido com sucesso."
        await self._speak_response(message)
        await self.notification_manager.add_notification(message, level=NOTIFICATION_SUCCESS)
        await self.event_manager.publish("KNOWLEDGE_DELETED", {"key": key})
        self.logger.info(message)
        return {"success": True, "output": message, "error": None}

    async def _list_knowledge_command(self) -> Dict[str, Any]:
        """
        Lista todas as chaves de conhecimento armazenadas.
        """
        await self._knowledge_loaded.wait()

        if not self._knowledge:
            message = "Nenhuma entrada de conhecimento armazenada."
            await self._speak_response(message)
            return {"success": True, "output": message, "error": None}
        
        knowledge_keys = list(self._knowledge.keys())
        output_lines = ["Conhecimento armazenado (chaves):"]
        output_lines.extend([f"- {key}" for key in knowledge_keys])
        
        message = "\n".join(output_lines)
        await self._speak_response(f"As suas entradas de conhecimento foram listadas. Verifique o ecr√£ para as chaves.")
        await self.notification_manager.add_notification("Lista de conhecimento exibida.", level=NOTIFICATION_INFO)
        return {"success": True, "output": message, "error": None}

    # --------------------------------------------------------------------- Plugin Interface

    def register_commands(self, executor: CommandExecutor) -> None:
        """Registers knowledge management commands with the CommandExecutor."""
        self.logger.info("A registar comandos do plugin KnowledgeManager...")
        executor.register_command("add_knowledge", self._add_knowledge_command)
        executor.register_command("get_knowledge", self._get_knowledge_command)
        executor.register_command("delete_knowledge", self._delete_knowledge_command)
        executor.register_command("list_knowledge", self._list_knowledge_command)
        self.logger.info("Comandos KnowledgeManager registados.")

    def get_tools_schema(self) -> List[Dict[str, Any]]:
        """
        Returns a list of tool definitions (schemas) for knowledge management features.
        These schemas are exposed to the LLM for function calling.
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": "add_knowledge",
                    "description": "Adiciona ou atualiza uma informa√ß√£o espec√≠fica (facto) que o GEM deve lembrar. Isso permite ao GEM aprender e personalizar as suas respostas com base no conhecimento fornecido pelo usu√°rio.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "key": {
                                "type": "string",
                                "description": "Uma chave ou nome √∫nico para a informa√ß√£o (ex: 'meu_endere√ßo', 'comida_favorita', 'nome_do_animal_de_estimacao').",
                            },
                            "value": {
                                "type": "string",
                                "description": "O valor ou conte√∫do da informa√ß√£o a ser armazenada (ex: 'Rua Principal, 123', 'pizza', 'Max').",
                            },
                            "source": {
                                "type": "string",
                                "description": "A origem do conhecimento. Padr√£o para 'user_input'.",
                                "default": "user_input"
                            }
                        },
                        "required": ["key", "value"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_knowledge",
                    "description": "Recupera uma informa√ß√£o espec√≠fica (facto) que o GEM aprendeu, utilizando a chave ou nome da informa√ß√£o. Use para responder a perguntas que dependem do conhecimento pr√©vio que o usu√°rio forneceu.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "key": {
                                "type": "string",
                                "description": "A chave ou nome da informa√ß√£o a ser recuperada.",
                            },
                        },
                        "required": ["key"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "delete_knowledge",
                    "description": "Remove uma entrada de conhecimento armazenada pelo seu nome ou chave. Esta a√ß√£o √© irrevers√≠vel.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "key": {
                                "type": "string",
                                "description": "A chave ou nome da informa√ß√£o a ser removida.",
                            },
                        },
                        "required": ["key"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "list_knowledge",
                    "description": "Lista todas as chaves (nomes) das informa√ß√µes que o GEM aprendeu e tem armazenadas. N√£o revela os valores das informa√ß√µes por padr√£o.",
                    "parameters": {"type": "object", "properties": {}, "required": []},
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
        """Performs any necessary cleanup."""
        self.logger.info("KnowledgeManager a ser desligado.")
        self.event_manager.unsubscribe("GEM_SHUTDOWN", self._on_gem_shutdown)
        self._knowledge.clear() # Clear in-memory knowledge


# =============================================================================
# CLI Test
# =============================================================================

if __name__ == "__main__":
    import asyncio
    
    # Configure logging for standalone test
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger("TestKnowledgeManager")

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

    async def run_knowledge_manager_tests():
        print("\n--- Iniciando Testes do KnowledgeManager ---")

        dummy_gem = DummyGEM(logger)
        knowledge_manager = KnowledgeManager(dummy_gem, logger)
        
        knowledge_manager.register_commands(dummy_gem.command_executor)

        await knowledge_manager.initialize()

        # --- Teste 1: Adicionar Conhecimento ---
        print("\n--- Teste 1: Adicionar Conhecimento ---")
        result_add_color = await dummy_gem.command_executor.execute("add_knowledge", key="minha_cor_favorita", value="azul")
        print(result_add_color["output"])
        assert result_add_color["success"] is True
        assert "Conhecimento 'minha_cor_favorita' adicionado/atualizado com sucesso." in result_add_color["output"]

        result_add_pet = await dummy_gem.command_executor.execute("add_knowledge", key="nome_do_animal_de_estimacao", value="Rex")
        print(result_add_pet["output"])
        assert result_add_pet["success"] is True

        # --- Teste 2: Listar Conhecimento ---
        print("\n--- Teste 2: Listar Conhecimento ---")
        result_list = await dummy_gem.command_executor.execute("list_knowledge")
        print(result_list["output"])
        assert result_list["success"] is True
        assert "minha_cor_favorita" in result_list["output"]
        assert "nome_do_animal_de_estimacao" in result_list["output"]

        # --- Teste 3: Obter Conhecimento ---
        print("\n--- Teste 3: Obter Conhecimento ---")
        result_get_color = await dummy_gem.command_executor.execute("get_knowledge", key="minha_cor_favorita")
        print(result_get_color["output"])
        assert result_get_color["success"] is True
        assert result_get_color["output"] == "azul"

        # --- Teste 4: Tentar obter conhecimento inexistente ---
        print("\n--- Teste 4: Tentar obter conhecimento inexistente ---")
        result_get_invalid = await dummy_gem.command_executor.execute("get_knowledge", key="comida_favorita")
        print(result_get_invalid["output"])
        assert result_get_invalid["success"] is False
        assert "Conhecimento 'comida_favorita' n√£o encontrado." in result_get_invalid["error"]

        # --- Teste 5: Atualizar Conhecimento ---
        print("\n--- Teste 5: Atualizar Conhecimento ---")
        result_update_color = await dummy_gem.command_executor.execute("add_knowledge", key="minha_cor_favorita", value="vermelho")
        print(result_update_color["output"])
        assert result_update_color["success"] is True
        
        updated_color = await dummy_gem.command_executor.execute("get_knowledge", key="minha_cor_favorita")
        assert updated_color["output"] == "vermelho"

        # --- Teste 6: Remover Conhecimento ---
        print("\n--- Teste 6: Remover Conhecimento ---")
        result_delete_pet = await dummy_gem.command_executor.execute("delete_knowledge", key="nome_do_animal_de_estimacao")
        print(result_delete_pet["output"])
        assert result_delete_pet["success"] is True
        assert "Conhecimento 'nome_do_animal_de_estimacao' removido com sucesso." in result_delete_pet["output"]

        # Verificar se foi removido
        result_list_after_delete = await dummy_gem.command_executor.execute("list_knowledge")
        assert "nome_do_animal_de_estimacao" not in result_list_after_delete["output"]

        print("\n--- Testes do KnowledgeManager conclu√≠dos com sucesso. ---")
        knowledge_manager.shutdown()
        
    asyncio.run(run_knowledge_manager_tests())

