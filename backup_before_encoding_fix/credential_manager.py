#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
💎 GEM OS - Credential Manager (core/credential_manager.py)
Manages secure storage and retrieval of user credentials and API keys.

Responsibilities
----------------
- Securely encrypt and store sensitive credentials.
- Provide mechanisms for retrieving credentials upon request.
- Add, update, and remove credentials.
- Expose credential management capabilities as tools for the LLM.
- Publish credential-related events.
- Integrate with NotificationManager for alerts.
"""

from __future__ import annotations

import asyncio
import logging
import os
import base64
from cryptography.fernet import Fernet # Para criptografia
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from typing import Any, Dict, List, Optional, Callable, Awaitable

from core.plugins import BasePlugin, CommandExecutor, GEMVoiceAssistant
from core.notification_manager import NotificationManager, NOTIFICATION_INFO, NOTIFICATION_WARNING, NOTIFICATION_ERROR

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

# --- Credential Manager como um Plugin ---
class CredentialManager(BasePlugin):
    """
    Manages secure storage and retrieval of user credentials for GEM OS, acting as a plugin.
    Uses Fernet for symmetric encryption.
    """
    STORAGE_KEY_CREDENTIALS = "gem_credentials"
    STORAGE_KEY_FERNET_KEY = "gem_fernet_key" # Master key for Fernet

    def __init__(self, gem_instance: GEMVoiceAssistant, logger: Optional[logging.Logger] = None):
        super().__init__(gem_instance, logger)
        self.logger.info("CredentialManager plugin inicializado.")
        
        self.event_manager: EventManager = gem_instance.event_manager
        self.notification_manager: NotificationManager = gem_instance.notification_manager
        self.storage: Storage = gem_instance.storage
        self.tts_module: TTSModule = gem_instance.tts_module

        self._fernet_key: Optional[bytes] = None
        self._fernet_instance: Optional[Fernet] = None
        self._credentials: Dict[str, str] = {} # {credential_name: encrypted_value}
        self._credentials_loaded = asyncio.Event()

    async def initialize(self) -> None:
        """Loads or generates the Fernet key and existing credentials."""
        await self._load_or_generate_fernet_key()
        await self._load_credentials_from_storage()
        self.event_manager.subscribe("GEM_SHUTDOWN", self._on_gem_shutdown)
        self.logger.info("CredentialManager inicializado.")

    async def _on_gem_shutdown(self, event_data: Dict[str, Any]) -> None:
        """Handler for GEM_SHUTDOWN event."""
        self.logger.info("Recebido GEM_SHUTDOWN. CredentialManager a ser desligado.")
        self.shutdown()

    async def _load_or_generate_fernet_key(self) -> None:
        """
        Loads the Fernet encryption key from storage, or generates a new one if not found.
        This key is crucial and should be protected.
        In a real-world scenario, this might be protected by a master password from the user.
        """
        key_str = await self.storage.get_setting(self.STORAGE_KEY_FERNET_KEY)
        if key_str:
            self._fernet_key = key_str.encode('utf-8')
            self.logger.info("Chave Fernet carregada do armazenamento.")
        else:
            self.logger.warning("Chave Fernet não encontrada. Gerando nova chave...")
            self._fernet_key = Fernet.generate_key()
            await self.storage.set_setting(self.STORAGE_KEY_FERNET_KEY, self._fernet_key.decode('utf-8'))
            self.logger.info("Nova chave Fernet gerada e salva no armazenamento.")
        
        self._fernet_instance = Fernet(self._fernet_key)

    async def _load_credentials_from_storage(self) -> None:
        """Loads encrypted credentials from persistent storage."""
        try:
            credentials_data = await self.storage.get_setting(self.STORAGE_KEY_CREDENTIALS, {})
            self._credentials = credentials_data
            self.logger.info(f"Carregadas {len(self._credentials)} credenciais (criptografadas) do armazenamento.")
        except Exception as e:
            self.logger.error(f"Falha ao carregar credenciais do armazenamento: {e}", exc_info=True)
        finally:
            self._credentials_loaded.set() # Sinaliza que as credenciais foram carregadas

    async def _save_credentials_to_storage(self) -> None:
        """Saves current encrypted credentials to persistent storage."""
        try:
            await self.storage.set_setting(self.STORAGE_KEY_CREDENTIALS, self._credentials)
            self.logger.debug(f"Salvas {len(self._credentials)} credenciais para o armazenamento.")
        except Exception as e:
            self.logger.error(f"Falha ao salvar credenciais no armazenamento: {e}", exc_info=True)

    def _encrypt(self, data: str) -> str:
        """Encrypts a string using Fernet."""
        if not self._fernet_instance:
            raise RuntimeError("Instância Fernet não inicializada.")
        return self._fernet_instance.encrypt(data.encode('utf-8')).decode('utf-8')

    def _decrypt(self, encrypted_data: str) -> str:
        """Decrypts a string using Fernet."""
        if not self._fernet_instance:
            raise RuntimeError("Instância Fernet não inicializada.")
        try:
            return self._fernet_instance.decrypt(encrypted_data.encode('utf-8')).decode('utf-8')
        except Exception as e:
            self.logger.error(f"Falha ao descriptografar dados: {e}", exc_info=True)
            raise ValueError("Falha na descriptografia. Chave inválida ou dados corrompidos.")

    # --------------------------------------------------------------------- Commands

    async def _add_credential_command(self, name: str, value: str) -> Dict[str, Any]:
        """
        Adiciona uma nova credencial. O valor será criptografado antes do armazenamento.
        """
        await self._credentials_loaded.wait()

        if not self._fernet_instance:
            message = "Gerenciador de credenciais não está pronto para operar (chave de criptografia ausente)."
            await self._speak_response(message)
            return {"success": False, "output": "", "error": message}

        encrypted_value = self._encrypt(value)
        self._credentials[name] = encrypted_value
        await self._save_credentials_to_storage()

        message = f"Credencial '{name}' adicionada com sucesso."
        await self._speak_response(message)
        await self.notification_manager.add_notification(message, level=NOTIFICATION_SUCCESS)
        await self.event_manager.publish("CREDENTIAL_ADDED", {"name": name})
        self.logger.info(message)
        return {"success": True, "output": message, "error": None}

    async def _get_credential_command(self, name: str) -> Dict[str, Any]:
        """
        Recupera e descriptografa uma credencial.
        Em um cenário real, isso exigiria uma forma de autenticação do usuário.
        """
        await self._credentials_loaded.wait()

        if not self._fernet_instance:
            message = "Gerenciador de credenciais não está pronto para operar (chave de criptografia ausente)."
            await self._speak_response(message)
            return {"success": False, "output": "", "error": message}

        encrypted_value = self._credentials.get(name)
        if not encrypted_value:
            message = f"Credencial '{name}' não encontrada."
            await self._speak_response(message)
            return {"success": False, "output": "", "error": message}
        
        try:
            decrypted_value = self._decrypt(encrypted_value)
            # NÃO FALE A CREDENCIAL REAL! Apenas confirme que foi recuperada.
            message = f"Credencial '{name}' recuperada com sucesso."
            await self._speak_response(message)
            await self.notification_manager.add_notification(message, level=NOTIFICATION_INFO)
            await self.event_manager.publish("CREDENTIAL_RETRIEVED", {"name": name, "value_preview": decrypted_value[:5] + "..."})
            self.logger.info(f"Credencial '{name}' recuperada (valor não logado/falado).")
            # Retorna o valor real para uso interno pelo CommandExecutor
            return {"success": True, "output": decrypted_value, "error": None}
        except ValueError as ve:
            message = f"Falha ao descriptografar credencial '{name}': {ve}"
            await self._speak_response(message)
            return {"success": False, "output": "", "error": message}

    async def _update_credential_command(self, name: str, new_value: str) -> Dict[str, Any]:
        """
        Atualiza o valor de uma credencial existente.
        """
        await self._credentials_loaded.wait()

        if not self._fernet_instance:
            message = "Gerenciador de credenciais não está pronto para operar (chave de criptografia ausente)."
            await self._speak_response(message)
            return {"success": False, "output": "", "error": message}

        if name not in self._credentials:
            message = f"Credencial '{name}' não encontrada para atualização."
            await self._speak_response(message)
            return {"success": False, "output": "", "error": message}

        encrypted_value = self._encrypt(new_value)
        self._credentials[name] = encrypted_value
        await self._save_credentials_to_storage()

        message = f"Credencial '{name}' atualizada com sucesso."
        await self._speak_response(message)
        await self.notification_manager.add_notification(message, level=NOTIFICATION_SUCCESS)
        await self.event_manager.publish("CREDENTIAL_UPDATED", {"name": name})
        self.logger.info(message)
        return {"success": True, "output": message, "error": None}

    async def _delete_credential_command(self, name: str) -> Dict[str, Any]:
        """
        Remove uma credencial.
        """
        await self._credentials_loaded.wait()

        if name not in self._credentials:
            message = f"Credencial '{name}' não encontrada para remoção."
            await self._speak_response(message)
            return {"success": False, "output": "", "error": message}

        del self._credentials[name]
        await self._save_credentials_to_storage()

        message = f"Credencial '{name}' removida com sucesso."
        await self._speak_response(message)
        await self.notification_manager.add_notification(message, level=NOTIFICATION_SUCCESS)
        await self.event_manager.publish("CREDENTIAL_DELETED", {"name": name})
        self.logger.info(message)
        return {"success": True, "output": message, "error": None}

    async def _list_credentials_command(self) -> Dict[str, Any]:
        """
        Lista os nomes de todas as credenciais armazenadas (não os valores).
        """
        await self._credentials_loaded.wait()

        if not self._credentials:
            message = "Nenhuma credencial armazenada."
            await self._speak_response(message)
            return {"success": True, "output": message, "error": None}
        
        credential_names = list(self._credentials.keys())
        output_lines = ["Credenciais armazenadas:"]
        output_lines.extend([f"- {name}" for name in credential_names])
        
        message = "\n".join(output_lines)
        await self._speak_response(f"As suas credenciais armazenadas foram listadas. Verifique o ecrã para os nomes.")
        await self.notification_manager.add_notification("Lista de credenciais exibida.", level=NOTIFICATION_INFO)
        return {"success": True, "output": message, "error": None}

    # --------------------------------------------------------------------- Plugin Interface

    def register_commands(self, executor: CommandExecutor) -> None:
        """Registers credential management commands with the CommandExecutor."""
        self.logger.info("A registar comandos do plugin CredentialManager...")
        executor.register_command("add_credential", self._add_credential_command)
        executor.register_command("get_credential", self._get_credential_command)
        executor.register_command("update_credential", self._update_credential_command)
        executor.register_command("delete_credential", self._delete_credential_command)
        executor.register_command("list_credentials", self._list_credentials_command)
        self.logger.info("Comandos CredentialManager registados.")

    def get_tools_schema(self) -> List[Dict[str, Any]]:
        """
        Returns a list of tool definitions (schemas) for credential management features.
        These schemas are exposed to the LLM for function calling.
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": "add_credential",
                    "description": "Adiciona uma nova credencial segura (ex: senha, chave API) ao gerenciador. O valor será criptografado. Requer o nome da credencial e o seu valor.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "O nome único da credencial (ex: 'chave_openai', 'senha_email').",
                            },
                            "value": {
                                "type": "string",
                                "description": "O valor real da credencial a ser armazenado.",
                            },
                        },
                        "required": ["name", "value"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_credential",
                    "description": "Recupera uma credencial segura pelo seu nome. O valor descriptografado é retornado para uso interno, mas não será vocalizado ou exibido diretamente para segurança. Use com cautela e apenas quando absolutamente necessário.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "O nome da credencial a ser recuperada.",
                            },
                        },
                        "required": ["name"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "update_credential",
                    "description": "Atualiza o valor de uma credencial existente. Requer o nome da credencial e o novo valor. O novo valor será criptografado.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "O nome da credencial a ser atualizada.",
                            },
                            "new_value": {
                                "type": "string",
                                "description": "O novo valor para a credencial.",
                            },
                        },
                        "required": ["name", "new_value"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "delete_credential",
                    "description": "Remove uma credencial armazenada pelo seu nome. Esta ação é irreversível.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "O nome da credencial a ser removida.",
                            },
                        },
                        "required": ["name"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "list_credentials",
                    "description": "Lista os nomes de todas as credenciais que estão atualmente armazenadas. Não revela os valores das credenciais por segurança.",
                    "parameters": {"type": "object", "properties": {}, "required": []},
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
        """Performs any necessary cleanup."""
        self.logger.info("CredentialManager a ser desligado.")
        # Clear sensitive data from memory when shutting down
        self._fernet_key = None
        self._fernet_instance = None
        self._credentials.clear() # Clear in-memory credentials
        self.event_manager.unsubscribe("GEM_SHUTDOWN", self._on_gem_shutdown)


# =============================================================================
# CLI Test
# =============================================================================

if __name__ == "__main__":
    import asyncio
    
    # Configure logging for standalone test
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger("TestCredentialManager")

    # --- Dummy Implementations for testing ---
    class DummyEventManager:
        def __init__(self, logger_instance):
            self.logger = logger_instance
        async def publish(self, event_type: str, data: Optional[Dict[str, Any]] = None) -> None:
            self.logger.info(f"Dummy EventManager: Publicado '{event_type}' com {data}")

    class DummyNotificationManager:
        def __init__(self, logger_instance):
            self.logger = logger_instance
        async def add_notification(self, message: str, level: str = NOTIFICATION_INFO, vocalize: bool = True) -> None:
            self.logger.info(f"Dummy Notification: [{level.upper()}] {message} (Vocalize: {vocalize})")
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

    async def run_credential_manager_tests():
        print("\n--- Iniciando Testes do CredentialManager ---")

        dummy_gem = DummyGEM(logger)
        credential_manager = CredentialManager(dummy_gem, logger)
        
        credential_manager.register_commands(dummy_gem.command_executor)

        await credential_manager.initialize()

        # --- Teste 1: Adicionar Credencial ---
        print("\n--- Teste 1: Adicionar Credencial ---")
        result_add = await dummy_gem.command_executor.execute("add_credential", name="minha_senha_secreta", value="senhaMuitoSegura123!")
        print(result_add["output"])
        assert result_add["success"] is True
        assert "Credencial 'minha_senha_secreta' adicionada com sucesso." in result_add["output"]

        result_add_api_key = await dummy_gem.command_executor.execute("add_credential", name="chave_openai", value="sk-xyz123abc")
        print(result_add_api_key["output"])
        assert result_add_api_key["success"] is True

        # --- Teste 2: Listar Credenciais ---
        print("\n--- Teste 2: Listar Credenciais ---")
        result_list = await dummy_gem.command_executor.execute("list_credentials")
        print(result_list["output"])
        assert result_list["success"] is True
        assert "minha_senha_secreta" in result_list["output"]
        assert "chave_openai" in result_list["output"]

        # --- Teste 3: Obter Credencial (valor não falado/logado diretamente) ---
        print("\n--- Teste 3: Obter Credencial ---")
        result_get = await dummy_gem.command_executor.execute("get_credential", name="minha_senha_secreta")
        print(result_get["output"])
        assert result_get["success"] is True
        assert result_get["output"] == "senhaMuitoSegura123!" # O output do comando deve ser o valor descriptografado
        assert "Credencial 'minha_senha_secreta' recuperada com sucesso." in dummy_gem.notification_manager._history[-1]["message"]

        # --- Teste 4: Tentar obter credencial inexistente ---
        print("\n--- Teste 4: Tentar obter credencial inexistente ---")
        result_get_invalid = await dummy_gem.command_executor.execute("get_credential", name="senha_inexistente")
        print(result_get_invalid["output"])
        assert result_get_invalid["success"] is False
        assert "Credencial 'senha_inexistente' não encontrada." in result_get_invalid["error"]

        # --- Teste 5: Atualizar Credencial ---
        print("\n--- Teste 5: Atualizar Credencial ---")
        result_update = await dummy_gem.command_executor.execute("update_credential", name="minha_senha_secreta", new_value="novaSenhaMuitoMelhor456!")
        print(result_update["output"])
        assert result_update["success"] is True
        assert "Credencial 'minha_senha_secreta' atualizada com sucesso." in result_update["output"]
        
        # Verificar se o valor foi realmente atualizado (obtendo e comparando)
        updated_value = await dummy_gem.command_executor.execute("get_credential", name="minha_senha_secreta")
        assert updated_value["output"] == "novaSenhaMuitoMelhor456!"

        # --- Teste 6: Remover Credencial ---
        print("\n--- Teste 6: Remover Credencial ---")
        result_delete = await dummy_gem.command_executor.execute("delete_credential", name="chave_openai")
        print(result_delete["output"])
        assert result_delete["success"] is True
        assert "Credencial 'chave_openai' removida com sucesso." in result_delete["output"]

        # Verificar se a credencial foi realmente removida
        result_list_after_delete = await dummy_gem.command_executor.execute("list_credentials")
        assert "chave_openai" not in result_list_after_delete["output"]

        print("\n--- Testes do CredentialManager concluídos com sucesso. ---")
        credential_manager.shutdown()
        
    asyncio.run(run_credential_manager_tests())

