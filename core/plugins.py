#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
💎 GEM OS - Plugin Manager (core/plugins.py)
Manages dynamic loading and registration of plugins for GEM OS.

Responsibilities
----------------
- Discover plugin modules in a specified directory.
- Dynamically load plugin classes.
- Register plugin-defined commands with the CommandExecutor.
- Provide tool definitions (schemas) from plugins to the LLMHandler.
"""

from __future__ import annotations

import importlib
import inspect
import logging
import os
import sys # Import adicionado para manipulação do sys.path
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Awaitable, Callable, Tuple # Adicionado Callable e Tuple para tipos mais precisos
from datetime import datetime # Adicionado para o ExamplePlugin

# Forward declarations to avoid circular imports during type hinting
# These will be resolved at runtime when GEMVoiceAssistant passes its components
class CommandExecutor:
    def __init__(self, gem_instance: Any, tts_module: Any, storage: Any, logger: Any): # Adicionado init para DummyCommandExecutor
        self.commands: Dict[str, Tuple[Callable[..., Awaitable[Dict[str, Any]]], Dict[str, Any]]] = {} # Ajustado o tipo
        self.logger = logger # Adicionado logger
        self.gem_instance = gem_instance # Adicionado para acesso ao gem_instance
    def register_command(self, name: str, func: Callable[..., Awaitable[Dict[str, Any]]], **kwargs) -> None:
        self.commands[name] = (func, kwargs)
        self.logger.debug(f"Comando '{name}' registado no CommandExecutor.")
    async def execute(self, command_name: str, *args, **kwargs) -> Dict[str, Any]:
        if command_name in self.commands:
            func, default_kwargs = self.commands[command_name]
            merged_kwargs = {**default_kwargs, **kwargs}
            self.logger.info(f"A executar comando '{command_name}' com args={args}, kwargs={merged_kwargs}")
            return await func(*args, **merged_kwargs)
        else:
            return {"success": False, "output": "", "error": f"Comando desconhecido: {command_name}"}


class LLMHandler:
    def set_available_tools(self, tools: List[Dict[str, Any]]) -> None:
        pass

class Storage:
    pass

class GEMVoiceAssistant:
    command_executor: CommandExecutor
    llm_handler: LLMHandler
    storage: Storage
    logger: logging.Logger
    gem_dir: Path # Adicionado para o PluginManager usar o path correto
    tts_module: Any # Adicionado para o _safe_tts_speak

# =============================================================================
# Base Plugin Class
# =============================================================================

class BasePlugin(ABC):
    """
    Abstract Base Class for all GEM OS plugins.
    All plugins must inherit from this class and implement its abstract methods.
    """
    def __init__(self, gem_instance: GEMVoiceAssistant, logger: logging.Logger):
        self.gem = gem_instance
        self.logger = logger
        self.name = self.__class__.__name__
        self.logger.debug(f"Plugin '{self.name}' inicializado.")

    @abstractmethod
    def register_commands(self, executor: CommandExecutor) -> None:
        """
        Registers commands provided by this plugin with the CommandExecutor.
        Each command should be an async function that returns a dict.
        Example: executor.register_command("say_hello", self._say_hello_command)
        """
        pass

    @abstractmethod
    def get_tools_schema(self) -> List[Dict[str, Any]]:
        """
        Returns a list of tool definitions (schemas) that this plugin exposes to the LLM.
        These schemas should follow the OpenAI function calling format.
        Example:
        [
            {
                "type": "function",
                "function": {
                    "name": "get_current_weather",
                    "description": "Get the current weather in a given location",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {
                                "type": "string",
                                "description": "The city and state, e.g. San Francisco, CA",
                            },
                            "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
                        },
                        "required": ["location"],
                    },
                },
            }
        ]
        """
        pass

    def shutdown(self) -> None:
        """
        Optional method for plugins to implement cleanup logic on shutdown.
        """
        self.logger.debug(f"Plugin '{self.name}' a desligar (implementação padrão).")
        pass

# =============================================================================
# Plugin Manager
# =============================================================================

class PluginManager:
    """
    Discovers, loads, and manages plugins for the GEM OS.
    It integrates plugin commands with the CommandExecutor and exposes tool schemas to the LLMHandler.
    """
    def __init__(self, gem_instance: GEMVoiceAssistant, plugin_dir: str = "plugins", logger: Optional[logging.Logger] = None):
        self.gem = gem_instance
        # Garante que plugin_dir seja um Path absoluto em relação ao gem_dir
        self.plugin_dir = (Path(gem_instance.gem_dir) / plugin_dir).resolve() if hasattr(gem_instance, 'gem_dir') else Path(plugin_dir).resolve()
        self.logger = logger or logging.getLogger(__name__)
        self.loaded_plugins: Dict[str, BasePlugin] = {}
        self.all_tools_schema: List[Dict[str, Any]] = []

        self.logger.info(f"PluginManager inicializado. Diretório de plugins: '{self.plugin_dir}'.")

    async def load_plugins(self) -> None:
        """
        Discovers and loads all plugins from the plugin directory.
        Registers their commands and collects their tool schemas.
        """
        self.logger.info(f"A escanear por plugins em '{self.plugin_dir}'...")
        if not self.plugin_dir.is_dir():
            self.logger.warning(f"Diretório de plugins '{self.plugin_dir}' não encontrado. Nenhum plugin será carregado.")
            return

        # Adicionar o diretório pai do plugin_dir ao sys.path para importação de módulos
        # Isso permite que plugins dentro de 'plugins/' sejam importados como 'plugins.my_plugin'
        if str(self.plugin_dir.parent) not in sys.path:
            sys.path.insert(0, str(self.plugin_dir.parent))

        for plugin_file in self.plugin_dir.iterdir():
            if plugin_file.suffix == ".py" and plugin_file.name != "__init__.py":
                module_name = f"{self.plugin_dir.name}.{plugin_file.stem}"
                self.logger.debug(f"A tentar carregar módulo: {module_name}")
                try:
                    # Usar importlib.util e importlib.machinery para carregar o módulo
                    # sem problemas com o sys.path se o nome do módulo for único.
                    spec = importlib.util.spec_from_file_location(module_name, plugin_file)
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)

                        for name, obj in inspect.getmembers(module):
                            if inspect.isclass(obj) and issubclass(obj, BasePlugin) and obj is not BasePlugin:
                                plugin_instance = obj(self.gem, self.logger)
                                self.loaded_plugins[plugin_instance.name] = plugin_instance
                                
                                # Registar comandos
                                if self.gem.command_executor:
                                    plugin_instance.register_commands(self.gem.command_executor)
                                    self.logger.info(f"Comandos registados para o plugin '{plugin_instance.name}'.")
                                else:
                                    self.logger.warning(f"CommandExecutor não disponível, a ignorar o registo de comandos para '{plugin_instance.name}'.")

                                # Recolher esquemas de ferramentas
                                tools = plugin_instance.get_tools_schema()
                                if tools:
                                    self.all_tools_schema.extend(tools)
                                    self.logger.debug(f"Recolhidas {len(tools)} ferramentas do plugin '{plugin_instance.name}'.")
                                break # Assumir uma classe de plugin por ficheiro
                except Exception as e:
                    self.logger.error(f"❌ Falha ao carregar plugin '{module_name}': {e}", exc_info=True)
        
        # Remover o diretório pai do plugin_dir do sys.path após o carregamento
        if str(self.plugin_dir.parent) in sys.path:
            sys.path.remove(str(self.plugin_dir.parent))

        self.logger.info(f"Carregados {len(self.loaded_plugins)} plugins com sucesso.")
        if self.gem.llm_handler and self.all_tools_schema:
            # Informar o LLMHandler sobre as ferramentas disponíveis
            if hasattr(self.gem.llm_handler, 'set_available_tools'):
                self.gem.llm_handler.set_available_tools(self.all_tools_schema)
                self.logger.info(f"Registadas {len(self.all_tools_schema)} ferramentas com o LLMHandler.")
            else:
                self.logger.warning("LLMHandler não tem o método 'set_available_tools'. Ferramentas não registadas com o LLM.")


    def get_all_tools_schema(self) -> List[Dict[str, Any]]:
        """
        Retorna uma lista consolidada de todos os esquemas de ferramentas de todos os plugins carregados.
        Esta lista é adequada para passar a um LLM para chamadas de função.
        """
        return self.all_tools_schema

    def get_plugin(self, name: str) -> Optional[BasePlugin]:
        """Retorna uma instância de plugin carregado pelo seu nome."""
        return self.loaded_plugins.get(name)

    def shutdown(self) -> None:
        """Invoca o método shutdown para todos os plugins carregados."""
        self.logger.info("A desligar o PluginManager e todos os plugins carregados.")
        for plugin_name, plugin_instance in self.loaded_plugins.items():
            try:
                plugin_instance.shutdown()
            except Exception as e:
                self.logger.error(f"Erro durante o desligamento do plugin '{plugin_name}': {e}", exc_info=True)

# =============================================================================
# Exemplo de Plugin (para demonstração e teste)
# Este plugin deve tipicamente residir no diretório 'plugins/'.
# =============================================================================
class ExamplePlugin(BasePlugin):
    def __init__(self, gem_instance: GEMVoiceAssistant, logger: logging.Logger):
        super().__init__(gem_instance, logger)
        self.logger.info("ExamplePlugin inicializado.")

    async def _say_hello_command(self, name: str = "mundo") -> Dict[str, Any]:
        """Um comando simples que faz o GEM dizer olá."""
        message = f"Olá, {name}! Eu sou o GEM."
        self.logger.info(f"ExamplePlugin: A executar _say_hello_command para {name}")
        # Assumindo que o GEM tem um módulo TTS para falar
        if self.gem and hasattr(self.gem, 'tts_module') and self.gem.tts_module:
            await self.gem.tts_module.speak(message)
        return {"success": True, "output": message, "error": None}

    async def _get_current_time_plugin_command(self) -> Dict[str, Any]:
        """Outro comando de exemplo para obter a hora atual."""
        current_time = datetime.now().strftime("%H:%M:%S")
        message = f"A hora atual, de acordo com o plugin, é {current_time}."
        self.logger.info(f"ExamplePlugin: A executar _get_current_time_plugin_command")
        if self.gem and hasattr(self.gem, 'tts_module') and self.gem.tts_module:
            await self.gem.tts_module.speak(message)
        return {"success": True, "output": message, "error": None}

    def register_commands(self, executor: CommandExecutor) -> None:
        """Regista os comandos de exemplo."""
        executor.register_command("say_hello", self._say_hello_command)
        executor.register_command("get_plugin_time", self._get_current_time_plugin_command)
        self.logger.info(f"ExamplePlugin registou comandos: 'say_hello', 'get_plugin_time'.")

    def get_tools_schema(self) -> List[Dict[str, Any]]:
        """Retorna o esquema de ferramentas para 'say_hello' para integração com o LLM."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "say_hello",
                    "description": "Faz o GEM cumprimentar alguém ou o mundo.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "O nome da pessoa ou entidade a ser cumprimentada. Padrão para 'mundo'.",
                            }
                        },
                        "required": [],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_plugin_time",
                    "description": "Obtém a hora atual do sistema através de um plugin.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                },
            }
        ]

# =============================================================================
# CLI Test
# =============================================================================

if __name__ == "__main__":
    import asyncio
    
    # Setup a dummy GEM instance for testing the PluginManager
    class DummyTTSModule: # Adicionado DummyTTSModule para o teste
        def __init__(self, logger):
            self.logger = logger
        async def speak(self, text: str) -> None:
            self.logger.info(f"Dummy TTS Module SPEAK: {text}")

    class DummyLLMHandler: # Adicionado DummyLLMHandler para o teste
        def __init__(self, logger):
            self.logger = logger
            self.tools: List[Dict[str, Any]] = []
        def set_available_tools(self, tools: List[Dict[str, Any]]) -> None:
            self.tools = tools
            self.logger.info(f"Dummy LLMHandler recebeu {len(tools)} ferramentas.")


    class DummyGEM:
        def __init__(self, logger):
            self.logger = logger
            self.gem_dir = Path(__file__).parent.parent # Project root
            self.tts_module = DummyTTSModule(logger) # Adicionado tts_module
            self.command_executor = CommandExecutor(self, self.tts_module, None, logger) # Pass self as dummy gem_instance, tts_module
            self.llm_handler = DummyLLMHandler(logger) # Minimal LLMHandler
            self.storage = type('DummyStorage', (), {})() # Minimal Storage
        
        # async def _safe_tts_speak(self, text: str): # Removido, usando self.tts_module.speak diretamente
        #     self.logger.info(f"Dummy TTS: {text}")

    # Set up basic logging for the test environment
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger("TestPluginManager")

    # Create a dummy plugin directory and an example plugin file
    test_plugin_dir = Path(__file__).parent.parent / "plugins" # Assume plugins/ is at project root
    # Ensure the parent directory is also considered for sys.path
    if test_plugin_dir.exists():
        for f in test_plugin_dir.iterdir(): # Limpa o diretório antes de criar
            if f.is_file():
                f.unlink()
    test_plugin_dir.mkdir(parents=True, exist_ok=True)
    example_plugin_file = test_plugin_dir / "example_plugin_test.py"
    
    # Write the content of ExamplePlugin to a temporary file
    example_plugin_content = """
import logging
from datetime import datetime
from typing import Dict, Any, List, Awaitable
from core.plugins import BasePlugin, CommandExecutor, GEMVoiceAssistant # Importar BasePlugin e outros do core.plugins

class ExamplePluginTest(BasePlugin):
    def __init__(self, gem_instance: GEMVoiceAssistant, logger: logging.Logger):
        super().__init__(gem_instance, logger)
        self.logger.info("ExamplePluginTest initialized.")

    async def _test_command_from_file(self, message: str = "teste") -> Dict[str, Any]:
        self.logger.info(f"ExamplePluginTest: Executando _test_command_from_file com: {message}")
        response = f"Comando de teste do plugin acionado com a mensagem: '{message}'"
        if self.gem and hasattr(self.gem, 'tts_module') and self.gem.tts_module:
            await self.gem.tts_module.speak(response)
        return {"success": True, "output": response, "error": None}

    def register_commands(self, executor: CommandExecutor) -> None:
        executor.register_command("plugin_test_command", self._test_command_from_file)
        self.logger.info("ExamplePluginTest registered 'plugin_test_command'.")

    def get_tools_schema(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "plugin_test_command",
                    "description": "Um comando de teste para verificar o carregamento de plugins.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "message": {
                                "type": "string",
                                "description": "Uma mensagem opcional para o comando de teste.",
                            }
                        },
                        "required": [],
                    },
                },
            }
        ]
"""
    with open(example_plugin_file, "w", encoding="utf-8") as f: # Adicionado encoding
        f.write(example_plugin_content)

    async def run_plugin_manager_tests():
        print("\n--- Iniciando Testes do PluginManager ---")

        dummy_gem = DummyGEM(logger)
        plugin_manager = PluginManager(dummy_gem, plugin_dir="plugins", logger=logger)
        
        await plugin_manager.load_plugins()

        print("\n--- Verificando Plugins Carregados ---")
        assert "ExamplePluginTest" in plugin_manager.loaded_plugins
        print(f"Plugins carregados: {list(plugin_manager.loaded_plugins.keys())}")

        print("\n--- Verificando Comandos Registrados ---")
        assert "plugin_test_command" in dummy_gem.command_executor.commands
        print(f"Comandos do CommandExecutor após carregamento de plugins: {list(dummy_gem.command_executor.commands.keys())}")

        print("\n--- Verificando Ferramentas (Tools) Coletadas ---")
        assert len(plugin_manager.get_all_tools_schema()) > 0
        print(f"Esquemas de Ferramentas coletados: {json.dumps(plugin_manager.get_all_tools_schema(), indent=2)}")

        print("\n--- Executando Comando de Plugin ---")
        result = await dummy_gem.command_executor.execute("plugin_test_command", message="Hello from plugin test!")
        print(f"Resultado do comando do plugin: {result}")
        assert result["success"] is True
        assert "Hello from plugin test!" in result["output"]

        print("\n--- Testando Shutdown de Plugins ---")
        plugin_manager.shutdown()
        print("✅ Testes do PluginManager concluídos com sucesso.")
        
        # Clean up temporary files and directories
        example_plugin_file.unlink()
        if test_plugin_dir.exists():
            test_plugin_dir.rmdir() # Remover o diretório de teste se estiver vazio

    asyncio.run(run_plugin_manager_tests())

