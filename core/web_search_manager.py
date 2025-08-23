#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
üíé GEM OS - Web Search Manager (core/web_search_manager.py)
Manages web search functionalities for GEM OS.

Responsibilities
----------------
- Execute web searches using a configurable search API.
- Process and format search results.
- Expose web search capabilities as tools for the LLM.
- Publish search-related events.
- Integrate with NotificationManager for alerts.
"""

from __future__ import annotations

import asyncio
import logging
import httpx # Para requisi√ß√µes HTTP ass√≠ncronas
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

# --- Dataclass para Resultados de Pesquisa ---
@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    source: Optional[str] = None
    rank: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "source": self.source,
            "rank": self.rank,
        }

# --- Web Search Manager como um Plugin ---
class WebSearchManager(BasePlugin):
    """
    Manages web search functionalities for GEM OS, acting as a plugin.
    """
    def __init__(self, gem_instance: GEMVoiceAssistant, logger: Optional[logging.Logger] = None):
        super().__init__(gem_instance, logger)
        self.logger.info("WebSearchManager plugin inicializado.")
        
        self.event_manager: EventManager = gem_instance.event_manager
        self.notification_manager: NotificationManager = gem_instance.notification_manager
        self.tts_module: TTSModule = gem_instance.tts_module
        self.config_manager: ConfigManager = gem_instance.config_manager

        self.search_api_base_url = self.config_manager.get_config().general.search_api_base_url
        self.search_api_key = os.getenv("SEARCH_API_KEY", self.config_manager.get_config().general.search_api_key)
        self.search_engine_id = os.getenv("SEARCH_ENGINE_ID", self.config_manager.get_config().general.search_engine_id)
        self._http_client = httpx.AsyncClient()

        if not self.search_api_key:
            self.logger.warning("SEARCH_API_KEY n√£o configurado. A pesquisa web pode n√£o funcionar.")
        if not self.search_engine_id:
            self.logger.warning("SEARCH_ENGINE_ID n√£o configurado. A pesquisa web pode n√£o funcionar.")

        self.logger.info(f"WebSearchManager configurado com URL base: {self.search_api_base_url}")

    async def initialize(self) -> None:
        """Performs any necessary setup for the web search manager."""
        self.event_manager.subscribe("GEM_SHUTDOWN", self._on_gem_shutdown)
        self.logger.info("WebSearchManager inicializado.")

    async def _on_gem_shutdown(self, event_data: Dict[str, Any]) -> None:
        """Handler for GEM_SHUTDOWN event to gracefully close HTTP client."""
        self.logger.info("Recebido GEM_SHUTDOWN. A fechar cliente HTTP do WebSearchManager.")
        await self.shutdown()

    async def _perform_web_search(self, query: str, num_results: int = 5) -> List[SearchResult]:
        """
        Performs a web search using the configured API and returns a list of SearchResult objects.
        
        Args:
            query: The search query string.
            num_results: The maximum number of results to retrieve.
            
        Returns:
            A list of SearchResult objects.
        """
        if not self.search_api_key or not self.search_engine_id:
            self.logger.error("API Key ou Search Engine ID ausentes. N√£o √© poss√≠vel realizar pesquisa.")
            await self._speak_response("Desculpe, a pesquisa web n√£o est√° configurada corretamente.")
            await self.notification_manager.add_notification(
                "Pesquisa web falhou: API Key ou Search Engine ID ausentes.", level=NOTIFICATION_ERROR
            )
            return []

        search_url = f"{self.search_api_base_url}/customsearch/v1"
        params = {
            "key": self.search_api_key,
            "cx": self.search_engine_id,
            "q": query,
            "num": num_results
        }

        self.logger.info(f"A realizar pesquisa web para: '{query}'")
        await self.event_manager.publish("WEB_SEARCH_STARTED", {"query": query})

        try:
            response = await self._http_client.get(search_url, params=params, timeout=10.0)
            response.raise_for_status() # Lan√ßa exce√ß√£o para c√≥digos de status HTTP 4xx/5xx
            data = response.json()

            results: List[SearchResult] = []
            if "items" in data:
                for i, item in enumerate(data["items"]):
                    results.append(SearchResult(
                        title=item.get("title", "Sem T√≠tulo"),
                        url=item.get("link", "#"),
                        snippet=item.get("snippet", "Sem snippet dispon√≠vel."),
                        source=item.get("displayLink"),
                        rank=i + 1
                    ))
            self.logger.info(f"Pesquisa web para '{query}' conclu√≠da. Encontrados {len(results)} resultados.")
            await self.notification_manager.add_notification(
                f"Pesquisa web conclu√≠da para '{query}'.", level=NOTIFICATION_SUCCESS, vocalize=False
            )
            await self.event_manager.publish("WEB_SEARCH_COMPLETED", {"query": query, "results_count": len(results)})
            return results

        except httpx.HTTPStatusError as e:
            error_msg = f"Erro HTTP ao realizar pesquisa web para '{query}': {e.response.status_code} - {e.response.text}"
            self.logger.error(error_msg, exc_info=True)
            await self.notification_manager.add_notification(f"Erro na pesquisa web: {e.response.status_code}", level=NOTIFICATION_ERROR)
            await self.tts_module.speak(f"Desculpe, houve um erro ao procurar na web: {e.response.status_code}.")
            return []
        except httpx.RequestError as e:
            error_msg = f"Erro de rede/requisi√ß√£o ao realizar pesquisa web para '{query}': {e}"
            self.logger.error(error_msg, exc_info=True)
            await self.notification_manager.add_notification(f"Erro de rede na pesquisa web.", level=NOTIFICATION_ERROR)
            await self.tts_module.speak(f"Desculpe, houve um problema de rede ao procurar na web.")
            return []
        except Exception as e:
            error_msg = f"Erro inesperado ao realizar pesquisa web para '{query}': {e}"
            self.logger.error(error_msg, exc_info=True)
            await self.notification_manager.add_notification(f"Erro inesperado na pesquisa web.", level=NOTIFICATION_ERROR)
            await self.tts_module.speak(f"Desculpe, ocorreu um erro inesperado ao procurar na web.")
            return []

    # --------------------------------------------------------------------- Commands

    async def _search_web_command(self, query: str, num_results: int = 3) -> Dict[str, Any]:
        """
        Executes a web search and returns formatted results.
        
        Args:
            query: The search query.
            num_results: The number of results to fetch.
            
        Returns:
            A dictionary with success status, output, and error.
        """
        if not query:
            message = "A consulta de pesquisa n√£o pode estar vazia."
            await self._speak_response(message)
            return {"success": False, "output": "", "error": message}

        results = await self._perform_web_search(query, num_results)

        if not results:
            message = f"N√£o foram encontrados resultados para '{query}'."
            await self._speak_response(message)
            return {"success": True, "output": message, "error": None}

        output_lines = [f"Resultados da pesquisa para '{query}':"]
        for i, result in enumerate(results):
            output_lines.append(f"{i+1}. {result.title}")
            output_lines.append(f"   URL: {result.url}")
            output_lines.append(f"   Snippet: {result.snippet}")
            output_lines.append("-" * 20)
        
        response_text = "\n".join(output_lines)
        await self._speak_response(f"Foram encontrados resultados para '{query}'. Verifique o ecr√£ para os detalhes.")
        return {"success": True, "output": response_text, "error": None}

    # --------------------------------------------------------------------- Plugin Interface

    def register_commands(self, executor: CommandExecutor) -> None:
        """Registers web search commands with the CommandExecutor."""
        self.logger.info("A registar comandos do plugin WebSearchManager...")
        executor.register_command("search_web", self._search_web_command)
        self.logger.info("Comandos WebSearchManager registados.")

    def get_tools_schema(self) -> List[Dict[str, Any]]:
        """
        Returns a list of tool definitions (schemas) for web search features.
        These schemas are exposed to the LLM for function calling.
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": "search_web",
                    "description": "Realiza uma pesquisa na web para uma determinada consulta e retorna os resultados mais relevantes. Use para responder a perguntas sobre factos, informa√ß√µes atuais ou conhecimento geral que n√£o estejam diretamente no seu conhecimento.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "A consulta de pesquisa a ser usada.",
                            },
                            "num_results": {
                                "type": "integer",
                                "description": "O n√∫mero m√°ximo de resultados de pesquisa a retornar. Padr√£o para 3.",
                                "default": 3
                            }
                        },
                        "required": ["query"],
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

    async def shutdown(self) -> None:
        """Closes the HTTP client and performs cleanup."""
        self.logger.info("WebSearchManager a ser desligado. A fechar o cliente HTTP.")
        if self._http_client:
            await self._http_client.aclose()
        self.event_manager.unsubscribe("GEM_SHUTDOWN", self._on_gem_shutdown)


# =============================================================================
# CLI Test
# =============================================================================

if __name__ == "__main__":
    import asyncio
    
    # Configure logging for standalone test
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger("TestWebSearchManager")

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
        def __init__(self):
            self.config = type('GEMConfig', (), {
                'general': type('GeneralConfig', (), {
                    'search_api_base_url': 'https://www.googleapis.com', # Google Custom Search API
                    'search_api_key': os.getenv("SEARCH_API_KEY", "YOUR_GOOGLE_SEARCH_API_KEY"), # Get this from Google Cloud Console
                    'search_engine_id': os.getenv("SEARCH_ENGINE_ID", "YOUR_CUSTOM_SEARCH_ENGINE_ID"), # Get this from Google Custom Search
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
            self.storage = type('DummyStorage', (), {})() # Not used directly by WebSearchManager

    async def run_web_search_manager_tests():
        print("\n--- Iniciando Testes do WebSearchManager ---")

        dummy_gem = DummyGEM(logger)
        web_search_manager = WebSearchManager(dummy_gem, logger)
        
        web_search_manager.register_commands(dummy_gem.command_executor)

        await web_search_manager.initialize()

        # Configurar vari√°veis de ambiente para o teste, se necess√°rio, ou usar as dummy keys
        # Lembre-se que para um teste real, voc√™ precisar√° de uma chave de API e um ID de motor de pesquisa v√°lidos.
        if not dummy_gem.config_manager.get_config().general.search_api_key == "YOUR_GOOGLE_SEARCH_API_KEY":
            print("\n--- Teste 1: Pesquisar na Web (consulta simples) ---")
            result_search = await dummy_gem.command_executor.execute("search_web", query="capital de Portugal")
            print(result_search["output"])
            assert result_search["success"] is True
            assert "Lisboa" in result_search["output"] # Esperado se a pesquisa for bem-sucedida

            print("\n--- Teste 2: Pesquisar na Web (m√∫ltiplos resultados) ---")
            result_search_multi = await dummy_gem.command_executor.execute("search_web", query="√∫ltimas not√≠cias de tecnologia", num_results=2)
            print(result_search_multi["output"])
            assert result_search_multi["success"] is True
            assert "Resultados da pesquisa para '√∫ltimas not√≠cias de tecnologia':" in result_search_multi["output"]

            print("\n--- Teste 3: Pesquisar na Web (sem resultados esperados) ---")
            result_no_results = await dummy_gem.command_executor.execute("search_web", query="asjdlfkasjdfaslkhflas", num_results=1) # Consulta aleat√≥ria
            print(result_no_results["output"])
            assert result_no_results["success"] is True
            assert "N√£o foram encontrados resultados para 'asjdlfkasjdfaslkhflas'." in result_no_results["output"]
        else:
            logger.warning("SEARCH_API_KEY ou SEARCH_ENGINE_ID n√£o configurados (usando valores dummy). Testes de pesquisa web reais ser√£o ignorados.")
            logger.warning("Para executar testes de pesquisa web reais, defina as vari√°veis de ambiente SEARCH_API_KEY e SEARCH_ENGINE_ID.")

        print("\n--- Teste 4: Pesquisar na Web (consulta vazia) ---")
        result_empty_query = await dummy_gem.command_executor.execute("search_web", query="")
        print(result_empty_query["output"])
        assert result_empty_query["success"] is False
        assert "A consulta de pesquisa n√£o pode estar vazia." in result_empty_query["error"]


        print("\n--- Testes do WebSearchManager conclu√≠dos com sucesso. ---")
        await web_search_manager.shutdown()
        
    asyncio.run(run_web_search_manager_tests())


