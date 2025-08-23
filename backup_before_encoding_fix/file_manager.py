#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
💎 GEM OS - File Manager (core/file_manager.py)
Manages file system operations, including listing, reading, writing, and manipulating files/directories.

Responsibilities
----------------
- List contents of directories.
- Read content from text files.
- Write or append content to files.
- Create and delete files/directories.
- Move and copy files/directories.
- Expose file system capabilities as tools for the LLM.
- Publish file system related events.
- Integrate with NotificationManager for alerts.
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil # Para operações de cópia/movimento
from pathlib import Path
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

# --- File Manager como um Plugin ---
class FileManager(BasePlugin):
    """
    Manages file system operations for GEM OS, acting as a plugin.
    """
    def __init__(self, gem_instance: GEMVoiceAssistant, logger: Optional[logging.Logger] = None):
        super().__init__(gem_instance, logger)
        self.logger.info("FileManager plugin inicializado.")
        
        self.event_manager: EventManager = gem_instance.event_manager
        self.notification_manager: NotificationManager = gem_instance.notification_manager
        self.tts_module: TTSModule = gem_instance.tts_module
        self.config_manager: ConfigManager = gem_instance.config_manager

        # Root directory for file operations (for security/sandboxing)
        self._base_path: Path = Path(self.config_manager.get_config().general.data_dir).resolve()
        self.logger.info(f"FileManager restrito ao caminho base: {self._base_path}")
        self._base_path.mkdir(parents=True, exist_ok=True) # Ensure base directory exists

    async def initialize(self) -> None:
        """Performs any necessary setup for the file manager."""
        self.event_manager.subscribe("GEM_SHUTDOWN", self._on_gem_shutdown)
        self.logger.info("FileManager inicializado.")

    async def _on_gem_shutdown(self, event_data: Dict[str, Any]) -> None:
        """Handler for GEM_SHUTDOWN event."""
        self.logger.info("Recebido GEM_SHUTDOWN. FileManager a ser desligado.")
        self.shutdown()

    def _resolve_path(self, path_str: str) -> Path:
        """Resolves a given path relative to the base path, ensuring it stays within the sandbox."""
        resolved = (self._base_path / path_str).resolve()
        if not str(resolved).startswith(str(self._base_path)):
            raise ValueError(f"Operação fora do caminho base permitida: {path_str}")
        return resolved

    # --------------------------------------------------------------------- Commands

    async def _list_files_and_directories_command(self, path: str = ".") -> Dict[str, Any]:
        """
        Lista o conteúdo de um diretório especificado.
        
        Args:
            path: O caminho do diretório a listar. Padrão para o diretório base.
        """
        try:
            target_path = self._resolve_path(path)
            if not target_path.is_dir():
                message = f"O caminho '{path}' não é um diretório válido ou não existe."
                await self._speak_response(message)
                return {"success": False, "output": "", "error": message}

            contents = [f.name for f in target_path.iterdir()]
            if not contents:
                message = f"O diretório '{path}' está vazio."
                await self._speak_response(message)
                return {"success": True, "output": message, "error": None}
            
            output_lines = [f"Conteúdo de '{path}':"]
            output_lines.extend(contents)
            
            message = "\n".join(output_lines)
            await self._speak_response(f"Conteúdo de {path} listado. Verifique o ecrã para os detalhes.")
            await self.notification_manager.add_notification(f"Conteúdo de {path} listado.", level=NOTIFICATION_INFO)
            await self.event_manager.publish("FILE_MANAGER_LISTED", {"path": path, "contents": contents})
            return {"success": True, "output": message, "error": None}
        except ValueError as ve:
            await self._speak_response(f"Erro de segurança: {ve}")
            return {"success": False, "output": "", "error": str(ve)}
        except Exception as e:
            error_message = f"Falha ao listar '{path}': {e}"
            self.logger.error(error_message, exc_info=True)
            await self._speak_response(error_message)
            return {"success": False, "output": "", "error": error_message}

    async def _read_file_content_command(self, file_path: str) -> Dict[str, Any]:
        """
        Lê e retorna o conteúdo de um ficheiro de texto.
        
        Args:
            file_path: O caminho para o ficheiro a ler.
        """
        try:
            target_file = self._resolve_path(file_path)
            if not target_file.is_file():
                message = f"O caminho '{file_path}' não é um ficheiro válido ou não existe."
                await self._speak_response(message)
                return {"success": False, "output": "", "error": message}
            
            # Limitar o tamanho do ficheiro para evitar carregar ficheiros muito grandes
            if target_file.stat().st_size > 1024 * 1024: # 1MB limit
                message = f"O ficheiro '{file_path}' é muito grande para ser lido (limite de 1MB)."
                await self._speak_response(message)
                return {"success": False, "output": "", "error": message}

            content = await asyncio.to_thread(target_file.read_text, encoding="utf-8")
            
            message = f"Conteúdo de '{file_path}':\n{content}"
            await self._speak_response(f"Conteúdo de {file_path} lido. Verifique o ecrã para os detalhes.")
            await self.notification_manager.add_notification(f"Ficheiro '{file_path}' lido.", level=NOTIFICATION_INFO)
            await self.event_manager.publish("FILE_MANAGER_READ", {"file_path": file_path, "content_preview": content[:100]})
            return {"success": True, "output": message, "error": None}
        except ValueError as ve:
            await self._speak_response(f"Erro de segurança: {ve}")
            return {"success": False, "output": "", "error": str(ve)}
        except UnicodeDecodeError:
            message = f"Não foi possível ler '{file_path}': Provavelmente não é um ficheiro de texto."
            await self._speak_response(message)
            return {"success": False, "output": "", "error": message}
        except Exception as e:
            error_message = f"Falha ao ler '{file_path}': {e}"
            self.logger.error(error_message, exc_info=True)
            await self._speak_response(error_message)
            return {"success": False, "output": "", "error": error_message}

    async def _write_to_file_command(self, file_path: str, content: str, append: bool = False) -> Dict[str, Any]:
        """
        Escreve ou anexa conteúdo a um ficheiro.
        
        Args:
            file_path: O caminho para o ficheiro a escrever.
            content: O conteúdo a escrever no ficheiro.
            append: Se verdadeiro, anexa o conteúdo; caso contrário, sobrescreve.
        """
        try:
            target_file = self._resolve_path(file_path)
            target_file.parent.mkdir(parents=True, exist_ok=True) # Ensure parent directory exists

            mode = "a" if append else "w"
            await asyncio.to_thread(target_file.write_text, content, encoding="utf-8", mode=mode)
            
            action = "anexado" if append else "escrito"
            message = f"Conteúdo {action} para '{file_path}' com sucesso."
            await self._speak_response(message)
            await self.notification_manager.add_notification(f"Conteúdo {action} para '{file_path}'.", level=NOTIFICATION_SUCCESS)
            await self.event_manager.publish("FILE_MANAGER_WRITTEN", {"file_path": file_path, "action": action})
            return {"success": True, "output": message, "error": None}
        except ValueError as ve:
            await self._speak_response(f"Erro de segurança: {ve}")
            return {"success": False, "output": "", "error": str(ve)}
        except Exception as e:
            error_message = f"Falha ao escrever para '{file_path}': {e}"
            self.logger.error(error_message, exc_info=True)
            await self._speak_response(error_message)
            return {"success": False, "output": "", "error": error_message}

    async def _create_directory_command(self, dir_path: str) -> Dict[str, Any]:
        """
        Cria um novo diretório (e diretórios pai se não existirem).
        
        Args:
            dir_path: O caminho do diretório a criar.
        """
        try:
            target_dir = self._resolve_path(dir_path)
            target_dir.mkdir(parents=True, exist_ok=False) # exist_ok=False para evitar erros se já existir
            
            message = f"Diretório '{dir_path}' criado com sucesso."
            await self._speak_response(message)
            await self.notification_manager.add_notification(message, level=NOTIFICATION_SUCCESS)
            await self.event_manager.publish("FILE_MANAGER_DIR_CREATED", {"dir_path": dir_path})
            return {"success": True, "output": message, "error": None}
        except FileExistsError:
            message = f"Diretório '{dir_path}' já existe."
            await self._speak_response(message)
            return {"success": False, "output": "", "error": message}
        except ValueError as ve:
            await self._speak_response(f"Erro de segurança: {ve}")
            return {"success": False, "output": "", "error": str(ve)}
        except Exception as e:
            error_message = f"Falha ao criar diretório '{dir_path}': {e}"
            self.logger.error(error_message, exc_info=True)
            await self._speak_response(error_message)
            return {"success": False, "output": "", "error": error_message}

    async def _delete_path_command(self, path: str, recursive: bool = False) -> Dict[str, Any]:
        """
        Apaga um ficheiro ou diretório.
        
        Args:
            path: O caminho para o ficheiro ou diretório a apagar.
            recursive: Se verdadeiro, apaga diretórios e seu conteúdo recursivamente.
        """
        try:
            target_path = self._resolve_path(path)
            if not target_path.exists():
                message = f"Caminho '{path}' não existe."
                await self._speak_response(message)
                return {"success": False, "output": "", "error": message}

            if target_path.is_file():
                await asyncio.to_thread(target_path.unlink)
                path_type = "Ficheiro"
            elif target_path.is_dir():
                if recursive:
                    await asyncio.to_thread(shutil.rmtree, target_path)
                    path_type = "Diretório (recursivo)"
                else:
                    await asyncio.to_thread(target_path.rmdir) # Apenas diretórios vazios
                    path_type = "Diretório (vazio)"
            else:
                message = f"Caminho '{path}' não é um ficheiro nem um diretório válido."
                await self._speak_response(message)
                return {"success": False, "output": "", "error": message}
            
            message = f"{path_type} '{path}' apagado com sucesso."
            await self._speak_response(message)
            await self.notification_manager.add_notification(message, level=NOTIFICATION_SUCCESS)
            await self.event_manager.publish("FILE_MANAGER_DELETED", {"path": path, "type": path_type})
            return {"success": True, "output": message, "error": None}
        except FileNotFoundError: # Should be caught by target_path.exists() but good for safety
            message = f"Caminho '{path}' não existe."
            await self._speak_response(message)
            return {"success": False, "output": "", "error": message}
        except OSError as e: # Catch non-empty directory errors without recursive=True
            if "Directory not empty" in str(e) or "Não está vazio" in str(e):
                message = f"O diretório '{path}' não está vazio. Use recursive=True para apagar o conteúdo."
                await self._speak_response(message)
                return {"success": False, "output": "", "error": message}
            error_message = f"Erro ao apagar '{path}': {e}"
            self.logger.error(error_message, exc_info=True)
            await self._speak_response(error_message)
            return {"success": False, "output": "", "error": error_message}
        except ValueError as ve:
            await self._speak_response(f"Erro de segurança: {ve}")
            return {"success": False, "output": "", "error": str(ve)}
        except Exception as e:
            error_message = f"Erro inesperado ao apagar '{path}': {e}"
            self.logger.error(error_message, exc_info=True)
            await self._speak_response(error_message)
            return {"success": False, "output": "", "error": error_message}

    async def _move_path_command(self, source_path: str, destination_path: str) -> Dict[str, Any]:
        """
        Move um ficheiro ou diretório de uma localização para outra.
        
        Args:
            source_path: O caminho de origem.
            destination_path: O caminho de destino.
        """
        try:
            source = self._resolve_path(source_path)
            destination = self._resolve_path(destination_path)

            if not source.exists():
                message = f"Caminho de origem '{source_path}' não existe."
                await self._speak_response(message)
                return {"success": False, "output": "", "error": message}
            
            if destination.exists():
                message = f"Caminho de destino '{destination_path}' já existe. Não será sobrescrito."
                await self._speak_response(message)
                return {"success": False, "output": "", "error": message}

            destination.parent.mkdir(parents=True, exist_ok=True) # Ensure parent directory exists for destination
            await asyncio.to_thread(shutil.move, source, destination)
            
            message = f"'{source_path}' movido para '{destination_path}' com sucesso."
            await self._speak_response(message)
            await self.notification_manager.add_notification(message, level=NOTIFICATION_SUCCESS)
            await self.event_manager.publish("FILE_MANAGER_MOVED", {"source": source_path, "destination": destination_path})
            return {"success": True, "output": message, "error": None}
        except ValueError as ve:
            await self._speak_response(f"Erro de segurança: {ve}")
            return {"success": False, "output": "", "error": str(ve)}
        except Exception as e:
            error_message = f"Falha ao mover '{source_path}' para '{destination_path}': {e}"
            self.logger.error(error_message, exc_info=True)
            await self._speak_response(error_message)
            return {"success": False, "output": "", "error": error_message}

    async def _copy_path_command(self, source_path: str, destination_path: str) -> Dict[str, Any]:
        """
        Copia um ficheiro ou diretório de uma localização para outra.
        
        Args:
            source_path: O caminho de origem.
            destination_path: O caminho de destino.
        """
        try:
            source = self._resolve_path(source_path)
            destination = self._resolve_path(destination_path)

            if not source.exists():
                message = f"Caminho de origem '{source_path}' não existe."
                await self._speak_response(message)
                return {"success": False, "output": "", "error": message}
            
            if destination.exists():
                message = f"Caminho de destino '{destination_path}' já existe. Não será sobrescrito."
                await self._speak_response(message)
                return {"success": False, "output": "", "error": message}

            destination.parent.mkdir(parents=True, exist_ok=True) # Ensure parent directory exists for destination
            
            if source.is_file():
                await asyncio.to_thread(shutil.copy2, source, destination)
                path_type = "Ficheiro"
            elif source.is_dir():
                await asyncio.to_thread(shutil.copytree, source, destination)
                path_type = "Diretório"
            else:
                message = f"Caminho de origem '{source_path}' não é um ficheiro nem um diretório válido."
                await self._speak_response(message)
                return {"success": False, "output": "", "error": message}

            message = f"{path_type} '{source_path}' copiado para '{destination_path}' com sucesso."
            await self._speak_response(message)
            await self.notification_manager.add_notification(message, level=NOTIFICATION_SUCCESS)
            await self.event_manager.publish("FILE_MANAGER_COPIED", {"source": source_path, "destination": destination_path})
            return {"success": True, "output": message, "error": None}
        except ValueError as ve:
            await self._speak_response(f"Erro de segurança: {ve}")
            return {"success": False, "output": "", "error": str(ve)}
        except Exception as e:
            error_message = f"Falha ao copiar '{source_path}' para '{destination_path}': {e}"
            self.logger.error(error_message, exc_info=True)
            await self._speak_response(error_message)
            return {"success": False, "output": "", "error": error_message}


    # --------------------------------------------------------------------- Plugin Interface

    def register_commands(self, executor: CommandExecutor) -> None:
        """Registers file management commands with the CommandExecutor."""
        self.logger.info("A registar comandos do plugin FileManager...")
        executor.register_command("list_files_and_directories", self._list_files_and_directories_command)
        executor.register_command("read_file_content", self._read_file_content_command)
        executor.register_command("write_to_file", self._write_to_file_command)
        executor.register_command("create_directory", self._create_directory_command)
        executor.register_command("delete_path", self._delete_path_command)
        executor.register_command("move_path", self._move_path_command)
        executor.register_command("copy_path", self._copy_path_command)
        self.logger.info("Comandos FileManager registados.")

    def get_tools_schema(self) -> List[Dict[str, Any]]:
        """
        Returns a list of tool definitions (schemas) for file management features.
        These schemas are exposed to the LLM for function calling.
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": "list_files_and_directories",
                    "description": "Lista o conteúdo (ficheiros e subdiretórios) de um diretório especificado. Por padrão, lista o diretório raiz do GEM.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "O caminho do diretório a listar. Use '.' para o diretório raiz do GEM. Ex: 'documentos/relatorios'",
                                "default": "."
                            }
                        },
                        "required": [],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "read_file_content",
                    "description": "Lê e retorna o conteúdo de um ficheiro de texto especificado. Não pode ler ficheiros binários ou muito grandes (limite de 1MB).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "O caminho para o ficheiro de texto a ler. Ex: 'documentos/notas.txt'",
                            }
                        },
                        "required": ["file_path"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "write_to_file",
                    "description": "Escreve ou anexa conteúdo a um ficheiro de texto. Se o ficheiro não existir, ele será criado. Use 'append: true' para adicionar ao final do ficheiro.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "O caminho para o ficheiro onde escrever. Ex: 'documentos/novo_relatorio.txt'",
                            },
                            "content": {
                                "type": "string",
                                "description": "O conteúdo de texto a ser escrito no ficheiro.",
                            },
                            "append": {
                                "type": "boolean",
                                "description": "Se verdadeiro, o conteúdo será anexado ao ficheiro existente. Se falso (padrão), o ficheiro será sobrescrito.",
                                "default": False
                            }
                        },
                        "required": ["file_path", "content"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "create_directory",
                    "description": "Cria um novo diretório no sistema de ficheiros do GEM. Diretórios pai necessários serão criados automaticamente.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "dir_path": {
                                "type": "string",
                                "description": "O caminho do novo diretório a ser criado. Ex: 'minhas_fotos/ferias_2024'",
                            }
                        },
                        "required": ["dir_path"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "delete_path",
                    "description": "Apaga um ficheiro ou um diretório. Para apagar um diretório não vazio, 'recursive' deve ser definido como verdadeiro.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "O caminho para o ficheiro ou diretório a apagar. Ex: 'documentos/antigo.txt' ou 'minha_pasta_vazia'",
                            },
                            "recursive": {
                                "type": "boolean",
                                "description": "Define se um diretório e seu conteúdo devem ser apagados recursivamente. Padrão para falso (apenas diretórios vazios).",
                                "default": False
                            }
                        },
                        "required": ["path"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "move_path",
                    "description": "Move um ficheiro ou diretório de um local para outro. O destino não pode já existir.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "source_path": {
                                "type": "string",
                                "description": "O caminho de origem do ficheiro ou diretório. Ex: 'downloads/documento.pdf'",
                            },
                            "destination_path": {
                                "type": "string",
                                "description": "O caminho de destino para onde mover o ficheiro ou diretório. Ex: 'documentos/documento_final.pdf'",
                            }
                        },
                        "required": ["source_path", "destination_path"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "copy_path",
                    "description": "Copia um ficheiro ou diretório de um local para outro. O destino não pode já existir.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "source_path": {
                                "type": "string",
                                "description": "O caminho de origem do ficheiro ou diretório. Ex: 'modelos/carta.docx'",
                            },
                            "destination_path": {
                                "type": "string",
                                "description": "O caminho de destino para onde copiar o ficheiro ou diretório. Ex: 'documentos/minhas_cartas/nova_carta.docx'",
                            }
                        },
                        "required": ["source_path", "destination_path"],
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
        """Performs any necessary cleanup."""
        self.logger.info("FileManager a ser desligado.")
        self.event_manager.unsubscribe("GEM_SHUTDOWN", self._on_gem_shutdown)


# =============================================================================
# CLI Test
# =============================================================================

if __name__ == "__main__":
    import asyncio
    import tempfile
    
    # Configure logging for standalone test
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger("TestFileManager")

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
        def __init__(self, temp_data_dir: Path):
            self.config = type('GEMConfig', (), {
                'general': type('GeneralConfig', (), {
                    'data_dir': str(temp_data_dir), # Use a temp dir for testing
                    'enable_audio_notifications': True
                })()
            })()
        def get_config(self) -> Any:
            return self.config

    class DummyGEM:
        def __init__(self, logger_instance: logging.Logger, temp_data_dir: Path):
            self.logger = logger_instance
            self.event_manager = DummyEventManager(logger_instance)
            self.notification_manager = DummyNotificationManager(logger_instance)
            self.tts_module = DummyTTSModule(logger_instance)
            self.config_manager = DummyConfigManager(temp_data_dir)
            self.command_executor = DummyCommandExecutor(logger_instance)
            self.storage = type('DummyStorage', (), {})() # Not used directly

    async def run_file_manager_tests():
        print("\n--- Iniciando Testes do FileManager ---")

        # Create a temporary directory for file manager operations to sandbox tests
        temp_data_dir = Path(tempfile.mkdtemp(prefix="gem_file_manager_test_"))
        logger.info(f"Diretório temporário para testes: {temp_data_dir}")

        dummy_gem = DummyGEM(logger, temp_data_dir)
        file_manager = FileManager(dummy_gem, logger)
        
        file_manager.register_commands(dummy_gem.command_executor)

        await file_manager.initialize()

        # --- Teste 1: Criar Diretório ---
        print("\n--- Teste 1: Criar Diretório ---")
        result_create_dir = await dummy_gem.command_executor.execute("create_directory", dir_path="documentos")
        print(result_create_dir["output"])
        assert result_create_dir["success"] is True
        assert "Diretório 'documentos' criado com sucesso." in result_create_dir["output"]
        assert (temp_data_dir / "documentos").is_dir()

        # --- Teste 2: Escrever para Ficheiro ---
        print("\n--- Teste 2: Escrever para Ficheiro ---")
        await dummy_gem.command_executor.execute("write_to_file", file_path="documentos/notas.txt", content="Isto é uma nota importante.")
        result_read_written = await dummy_gem.command_executor.execute("read_file_content", file_path="documentos/notas.txt")
        print(result_read_written["output"])
        assert result_read_written["success"] is True
        assert "Isto é uma nota importante." in result_read_written["output"]

        # --- Teste 3: Anexar a Ficheiro ---
        print("\n--- Teste 3: Anexar a Ficheiro ---")
        await dummy_gem.command_executor.execute("write_to_file", file_path="documentos/notas.txt", content="\nMais uma linha.", append=True)
        result_read_appended = await dummy_gem.command_executor.execute("read_file_content", file_path="documentos/notas.txt")
        print(result_read_appended["output"])
        assert result_read_appended["success"] is True
        assert "Isto é uma nota importante.\nMais uma linha." in result_read_appended["output"]

        # --- Teste 4: Listar Conteúdo do Diretório ---
        print("\n--- Teste 4: Listar Conteúdo do Diretório ---")
        result_list_dir = await dummy_gem.command_executor.execute("list_files_and_directories", path="documentos")
        print(result_list_dir["output"])
        assert result_list_dir["success"] is True
        assert "notas.txt" in result_list_dir["output"]

        # --- Teste 5: Criar Subdiretório ---
        print("\n--- Teste 5: Criar Subdiretório ---")
        result_create_subdir = await dummy_gem.command_executor.execute("create_directory", dir_path="documentos/relatorios")
        print(result_create_subdir["output"])
        assert result_create_subdir["success"] is True
        assert (temp_data_dir / "documentos" / "relatorios").is_dir()

        # --- Teste 6: Copiar Ficheiro ---
        print("\n--- Teste 6: Copiar Ficheiro ---")
        await dummy_gem.command_executor.execute("copy_path", source_path="documentos/notas.txt", destination_path="documentos/relatorios/backup_notas.txt")
        assert (temp_data_dir / "documentos" / "relatorios" / "backup_notas.txt").is_file()
        result_read_copied = await dummy_gem.command_executor.execute("read_file_content", file_path="documentos/relatorios/backup_notas.txt")
        print(result_read_copied["output"])
        assert result_read_copied["success"] is True
        assert "Isto é uma nota importante.\nMais uma linha." in result_read_copied["output"]

        # --- Teste 7: Mover Ficheiro ---
        print("\n--- Teste 7: Mover Ficheiro ---")
        await dummy_gem.command_executor.execute("write_to_file", file_path="documentos/temp_file.txt", content="Conteúdo temporário.")
        result_move = await dummy_gem.command_executor.execute("move_path", source_path="documentos/temp_file.txt", destination_path="temp_moved.txt")
        print(result_move["output"])
        assert result_move["success"] is True
        assert not (temp_data_dir / "documentos" / "temp_file.txt").exists()
        assert (temp_data_dir / "temp_moved.txt").is_file()

        # --- Teste 8: Apagar Ficheiro ---
        print("\n--- Teste 8: Apagar Ficheiro ---")
        result_delete_file = await dummy_gem.command_executor.execute("delete_path", path="temp_moved.txt")
        print(result_delete_file["output"])
        assert result_delete_file["success"] is True
        assert not (temp_data_dir / "temp_moved.txt").exists()

        # --- Teste 9: Apagar Diretório Vazio ---
        print("\n--- Teste 9: Apagar Diretório Vazio ---")
        await dummy_gem.command_executor.execute("create_directory", dir_path="pasta_vazia")
        assert (temp_data_dir / "pasta_vazia").is_dir()
        result_delete_empty_dir = await dummy_gem.command_executor.execute("delete_path", path="pasta_vazia")
        print(result_delete_empty_dir["output"])
        assert result_delete_empty_dir["success"] is True
        assert not (temp_data_dir / "pasta_vazia").exists()

        # --- Teste 10: Tentar apagar diretório não vazio sem recursive ---
        print("\n--- Teste 10: Tentar apagar diretório não vazio sem recursive ---")
        result_delete_non_empty_fail = await dummy_gem.command_executor.execute("delete_path", path="documentos")
        print(result_delete_non_empty_fail["output"])
        assert result_delete_non_empty_fail["success"] is False
        assert "não está vazio" in result_delete_non_empty_fail["error"]

        # --- Teste 11: Apagar Diretório Não Vazio (recursivo) ---
        print("\n--- Teste 11: Apagar Diretório Não Vazio (recursivo) ---")
        result_delete_recursive = await dummy_gem.command_executor.execute("delete_path", path="documentos", recursive=True)
        print(result_delete_recursive["output"])
        assert result_delete_recursive["success"] is True
        assert not (temp_data_dir / "documentos").exists()

        # --- Teste 12: Tentativa de operação fora do sandbox ---
        print("\n--- Teste 12: Tentativa de operação fora do sandbox ---")
        result_sandbox_fail = await dummy_gem.command_executor.execute("read_file_content", file_path="../gem_runner.sh")
        print(result_sandbox_fail["output"])
        assert result_sandbox_fail["success"] is False
        assert "Erro de segurança: Operação fora do caminho base permitida" in result_sandbox_fail["error"]


        print("\n--- Testes do FileManager concluídos com sucesso. ---")
        file_manager.shutdown()
        
        # Cleanup the temporary directory
        if temp_data_dir.exists():
            shutil.rmtree(temp_data_dir)
            logger.info(f"Diretório temporário de teste {temp_data_dir} limpo.")

    asyncio.run(run_file_manager_tests())

