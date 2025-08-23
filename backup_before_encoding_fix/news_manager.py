#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
💎 GEM OS - News Manager (core/news_manager.py)
Manages fetching, filtering, and presenting news from configurable sources.

Responsibilities
----------------
- Fetch news articles from a configured news API.
- Filter news by categories, topics, keywords, or sources.
- Process and format news article details.
- Expose news capabilities as tools for the LLM.
- Publish news-related events.
- Integrate with NotificationManager for alerts.
"""

from __future__ import annotations

import asyncio
import logging
import httpx # Para requisições HTTP assíncronas
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable, Awaitable, Tuple

from core.plugins import BasePlugin, CommandExecutor, GEMVoiceAssistant
from core.notification_manager import NotificationManager, NOTIFICATION_INFO, NOTIFICATION_WARNING, NOTIFICATION_SUCCESS

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

# --- Dataclass para Artigo de Notícia ---
@dataclass
class NewsArticle:
    title: str
    description: str
    url: str
    source_name: str
    published_at: datetime
    author: Optional[str] = None
    category: Optional[str] = None # Pode ser inferido ou fornecido pela API

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "description": self.description,
            "url": self.url,
            "source_name": self.source_name,
            "published_at": self.published_at.isoformat(),
            "author": self.author,
            "category": self.category,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> NewsArticle:
        return cls(
            title=data["title"],
            description=data["description"],
            url=data["url"],
            source_name=data["source_name"],
            published_at=datetime.fromisoformat(data["published_at"]),
            author=data.get("author"),
            category=data.get("category"),
        )

# --- News Manager como um Plugin ---
class NewsManager(BasePlugin):
    """
    Manages fetching and presenting news for GEM OS, acting as a plugin.
    """
    def __init__(self, gem_instance: GEMVoiceAssistant, logger: Optional[logging.Logger] = None):
        super().__init__(gem_instance, logger)
        self.logger.info("NewsManager plugin inicializado.")
        
        self.event_manager: EventManager = gem_instance.event_manager
        self.notification_manager: NotificationManager = gem_instance.notification_manager
        self.tts_module: TTSModule = gem_instance.tts_module
        self.config_manager: ConfigManager = gem_instance.config_manager

        self._news_api_base_url = self.config_manager.get_config().general.news_api_base_url
        self._news_api_key = os.getenv("NEWS_API_KEY", self.config_manager.get_config().general.news_api_key)
        self._default_news_language = self.config_manager.get_config().general.default_news_language
        self._http_client = httpx.AsyncClient()

        if not self._news_api_key:
            self.logger.warning("NEWS_API_KEY não configurado. O gerenciador de notícias pode não funcionar.")
        
        self.logger.info(f"NewsManager configurado com URL base: {self._news_api_base_url}, Idioma padrão: {self._default_news_language}")

    async def initialize(self) -> None:
        """Performs any necessary setup for the news manager."""
        self.event_manager.subscribe("GEM_SHUTDOWN", self._on_gem_shutdown)
        self.logger.info("NewsManager inicializado.")

    async def _on_gem_shutdown(self, event_data: Dict[str, Any]) -> None:
        """Handler for GEM_SHUTDOWN event to gracefully close HTTP client."""
        self.logger.info("Recebido GEM_SHUTDOWN. A fechar cliente HTTP do NewsManager.")
        await self.shutdown()

    async def _fetch_news(self, query: Optional[str] = None, category: Optional[str] = None,
                         sources: Optional[str] = None, language: Optional[str] = None,
                         page_size: int = 5) -> List[NewsArticle]:
        """
        Fetches news articles from the configured API.
        
        Args:
            query: Palavras-chave para pesquisar nas notícias.
            category: Categoria da notícia (ex: 'technology', 'sports').
            sources: Uma lista de IDs de fontes separadas por vírgula.
            language: Código do idioma (ex: 'pt', 'en'). Padrão para o idioma de configuração.
            page_size: Número máximo de artigos a retornar.
            
        Returns:
            Uma lista de objetos NewsArticle.
        """
        if not self._news_api_key:
            self.logger.error("API Key da News API ausente. Não é possível buscar notícias.")
            await self._speak_response("Desculpe, a busca de notícias não está configurada corretamente.")
            await self.notification_manager.add_notification(
                "Busca de notícias falhou: API Key ausente.", level=NOTIFICATION_ERROR
            )
            return []

        search_url = f"{self._news_api_base_url}/v2/top-headlines" # Exemplo para NewsAPI.org
        params = {
            "apiKey": self._news_api_key,
            "pageSize": page_size,
            "language": language or self._default_news_language,
        }
        if query:
            params["q"] = query
        if category:
            params["category"] = category
        if sources:
            params["sources"] = sources

        self.logger.info(f"A buscar notícias com os parâmetros: {params}")
        await self.event_manager.publish("NEWS_FETCH_STARTED", {"params": params})

        try:
            response = await self._http_client.get(search_url, params=params, timeout=15.0)
            response.raise_for_status()
            data = response.json()

            articles: List[NewsArticle] = []
            if "articles" in data:
                for item in data["articles"]:
                    # Garantir que todos os campos obrigatórios estão presentes e não são None
                    title = item.get("title")
                    description = item.get("description")
                    url = item.get("url")
                    source_name = item.get("source", {}).get("name")
                    published_at_str = item.get("publishedAt")

                    if all([title, description, url, source_name, published_at_str]):
                        try:
                            published_at = datetime.fromisoformat(published_at_str.replace('Z', '+00:00'))
                        except ValueError:
                            published_at = datetime.now() # Fallback
                            self.logger.warning(f"Não foi possível analisar 'publishedAt': {published_at_str}. A usar a hora atual.")

                        articles.append(NewsArticle(
                            title=title,
                            description=description,
                            url=url,
                            source_name=source_name,
                            published_at=published_at,
                            author=item.get("author"),
                            category=category # Usar a categoria que foi passada na requisição, se houver
                        ))
            self.logger.info(f"Busca de notícias concluída. Encontrados {len(articles)} artigos.")
            await self.notification_manager.add_notification(
                f"Notícias obtidas. Encontrados {len(articles)} artigos.", level=NOTIFICATION_SUCCESS, vocalize=False
            )
            await self.event_manager.publish("NEWS_FETCH_COMPLETED", {"articles_count": len(articles)})
            return articles

        except httpx.HTTPStatusError as e:
            error_msg = f"Erro HTTP ao buscar notícias: {e.response.status_code} - {e.response.text}"
            self.logger.error(error_msg, exc_info=True)
            await self.notification_manager.add_notification(f"Erro na busca de notícias: {e.response.status_code}", level=NOTIFICATION_ERROR)
            await self.tts_module.speak(f"Desculpe, houve um erro ao buscar notícias: {e.response.status_code}.")
            return []
        except httpx.RequestError as e:
            error_msg = f"Erro de rede/requisição ao buscar notícias: {e}"
            self.logger.error(error_msg, exc_info=True)
            await self.notification_manager.add_notification(f"Erro de rede na busca de notícias.", level=NOTIFICATION_ERROR)
            await self.tts_module.speak(f"Desculpe, houve um problema de rede ao buscar notícias.")
            return []
        except Exception as e:
            error_msg = f"Erro inesperado ao buscar notícias: {e}"
            self.logger.error(error_msg, exc_info=True)
            await self.notification_manager.add_notification(f"Erro inesperado na busca de notícias.", level=NOTIFICATION_ERROR)
            await self.tts_module.speak(f"Desculpe, ocorreu um erro inesperado ao buscar notícias.")
            return []

    # --------------------------------------------------------------------- Commands

    async def _get_news_command(self, query: Optional[str] = None, category: Optional[str] = None,
                               sources: Optional[str] = None, page_size: int = 3,
                               language: Optional[str] = None) -> Dict[str, Any]:
        """
        Obtém e apresenta artigos de notícias.
        
        Args:
            query: Palavras-chave para pesquisar.
            category: Categoria das notícias (ex: 'tecnologia', 'desporto').
            sources: IDs de fontes de notícias separadas por vírgula.
            page_size: Número máximo de artigos a retornar.
            language: Idioma das notícias (ex: 'pt', 'en').
        """
        articles = await self._fetch_news(query, category, sources, language, page_size)

        if not articles:
            message = "Não foram encontrados artigos de notícias com os critérios especificados."
            await self._speak_response(message)
            return {"success": True, "output": message, "error": None}
        
        output_lines = ["Principais Notícias:"]
        for i, article in enumerate(articles):
            output_lines.append(f"{i+1}. {article.title} - Fonte: {article.source_name} (Publicado em: {article.published_at.strftime('%Y-%m-%d %H:%M')})")
            output_lines.append(f"   Descrição: {article.description}")
            output_lines.append(f"   Leia mais: {article.url}")
            output_lines.append("-" * 20)
        
        message = "\n".join(output_lines)
        await self._speak_response(f"Notícias obtidas. Verifique o ecrã para os artigos mais recentes.")
        return {"success": True, "output": message, "error": None}

    # --------------------------------------------------------------------- Plugin Interface

    def register_commands(self, executor: CommandExecutor) -> None:
        """Registers news management commands with the CommandExecutor."""
        self.logger.info("A registar comandos do plugin NewsManager...")
        executor.register_command("get_news", self._get_news_command)
        self.logger.info("Comandos NewsManager registados.")

    def get_tools_schema(self) -> List[Dict[str, Any]]:
        """
        Returns a list of tool definitions (schemas) for news features.
        These schemas are exposed to the LLM for function calling.
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_news",
                    "description": "Obtém e apresenta artigos de notícias recentes de fontes configuradas. Pode filtrar por palavras-chave, categoria, fontes específicas e número de resultados.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Palavras-chave para pesquisar nas notícias (ex: 'inteligência artificial', 'economia do Brasil'). Opcional.",
                            },
                            "category": {
                                "type": "string",
                                "description": "Categoria das notícias (ex: 'business', 'entertainment', 'general', 'health', 'science', 'sports', 'technology'). Opcional.",
                                "enum": ["business", "entertainment", "general", "health", "science", "sports", "technology"]
                            },
                            "sources": {
                                "type": "string",
                                "description": "Uma lista de IDs de fontes de notícias separadas por vírgula (ex: 'bbc-news,the-verge'). Opcional.",
                            },
                            "page_size": {
                                "type": "integer",
                                "description": "O número máximo de artigos de notícias a retornar. Padrão para 3, máximo de 10.",
                                "default": 3,
                                "minimum": 1,
                                "maximum": 10
                            },
                            "language": {
                                "type": "string",
                                "description": "O código do idioma para as notícias (ex: 'pt' para português, 'en' para inglês). Padrão para o idioma configurado do GEM.",
                                "enum": ["ar", "de", "en", "es", "fr", "he", "it", "nl", "no", "pt", "ru", "sv", "ud", "zh"]
                            }
                        },
                        "required": [],
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

    async def shutdown(self) -> None:
        """Closes the HTTP client and performs cleanup."""
        self.logger.info("NewsManager a ser desligado. A fechar o cliente HTTP.")
        if self._http_client:
            await self._http_client.aclose()
        self.event_manager.unsubscribe("GEM_SHUTDOWN", self._on_gem_shutdown)


# =============================================================================
# CLI Test
# =============================================================================

if __name__ == "__main__":
    import asyncio
    import os # Importar para variáveis de ambiente
    
    # Configure logging for standalone test
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger("TestNewsManager")

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
                    'news_api_base_url': 'https://newsapi.org', # Base URL para a NewsAPI.org
                    'news_api_key': os.getenv("NEWS_API_KEY", "YOUR_NEWS_API_KEY"), # Obtenha em newsapi.org
                    'default_news_language': 'pt',
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
            self.storage = type('DummyStorage', (), {})() # Not used directly

    # Mock the httpx.AsyncClient.get for testing without a real API call
    async def mock_httpx_get(*args, **kwargs):
        class MockResponse:
            def __init__(self, status_code, json_data):
                self.status_code = status_code
                self._json_data = json_data
            
            def raise_for_status(self):
                if 400 <= self.status_code < 600:
                    raise httpx.HTTPStatusError(f"HTTP Error: {self.status_code}", request=None, response=self)
            
            def json(self):
                return self._json_data
            
            @property
            def text(self):
                return json.dumps(self._json_data)

        # Simulate different API responses
        if kwargs.get('params', {}).get('q') == "tecnologia" and kwargs.get('params', {}).get('category') == "technology":
            logger.info("Mocking news for 'tecnologia' in 'technology' category.")
            return MockResponse(200, {
                "status": "ok",
                "totalResults": 2,
                "articles": [
                    {
                        "source": {"id": "the-verge", "name": "The Verge"},
                        "author": "Tech Reporter",
                        "title": "Nova Inovação em IA Anunciada",
                        "description": "Uma nova e revolucionária tecnologia de IA foi revelada hoje.",
                        "url": "https://www.theverge.com/ai-innovation",
                        "urlToImage": "https://example.com/ai.jpg",
                        "publishedAt": "2025-08-22T10:00:00Z",
                        "content": "Detalhes completos da inovação..."
                    },
                    {
                        "source": {"id": "techcrunch", "name": "TechCrunch"},
                        "author": "Gizmo Editor",
                        "title": "Smartphones do Futuro: O Que Esperar?",
                        "description": "Uma análise profunda das tendências que moldarão os smartphones nos próximos anos.",
                        "url": "https://techcrunch.com/future-phones",
                        "urlToImage": "https://example.com/phone.jpg",
                        "publishedAt": "2025-08-22T09:30:00Z",
                        "content": "Mais detalhes sobre smartphones..."
                    }
                ]
            })
        elif kwargs.get('params', {}).get('category') == "sports" and kwargs.get('params', {}).get('language') == "pt":
            logger.info("Mocking news for 'sports' in 'pt' language.")
            return MockResponse(200, {
                "status": "ok",
                "totalResults": 1,
                "articles": [
                    {
                        "source": {"id": "abola", "name": "A Bola"},
                        "author": "Jornalista Desportivo",
                        "title": "Benfica Vence Clássico com Golo no Último Minuto",
                        "description": "Um resumo emocionante da vitória do Benfica no jogo de ontem.",
                        "url": "https://abola.pt/benfica-vence",
                        "urlToImage": "https://example.com/benfica.jpg",
                        "publishedAt": "2025-08-22T08:00:00Z",
                        "content": "Relato da partida..."
                    }
                ]
            })
        elif kwargs.get('params', {}).get('q') == "consulta sem resultados":
            logger.info("Mocking no results for 'consulta sem resultados'.")
            return MockResponse(200, {
                "status": "ok",
                "totalResults": 0,
                "articles": []
            })
        elif kwargs.get('params', {}).get('q') == "erro api":
            logger.info("Mocking API error for 'erro api'.")
            return MockResponse(403, {"status": "error", "code": "apiKeyInvalid", "message": "Your API key is invalid or incorrect."})
        else:
            logger.warning(f"No specific mock for parameters: {kwargs.get('params')}. Returning empty.")
            return MockResponse(200, {"status": "ok", "totalResults": 0, "articles": []})

    # Patch httpx.AsyncClient.get with our mock for testing
    original_httpx_get = httpx.AsyncClient.get
    httpx.AsyncClient.get = mock_httpx_get

    async def run_news_manager_tests():
        print("\n--- Iniciando Testes do NewsManager ---")

        dummy_gem = DummyGEM(logger)
        news_manager = NewsManager(dummy_gem, logger)
        
        news_manager.register_commands(dummy_gem.command_executor)

        await news_manager.initialize()

        # --- Teste 1: Obter Notícias por Categoria e Query ---
        print("\n--- Teste 1: Obter Notícias por Categoria e Query ---")
        result_news_tech = await dummy_gem.command_executor.execute(
            "get_news", query="tecnologia", category="technology", page_size=2
        )
        print(result_news_tech["output"])
        assert result_news_tech["success"] is True
        assert "Nova Inovação em IA Anunciada" in result_news_tech["output"]
        assert "Smartphones do Futuro: O Que Esperar?" in result_news_tech["output"]

        # --- Teste 2: Obter Notícias por Categoria e Idioma ---
        print("\n--- Teste 2: Obter Notícias por Categoria e Idioma ---")
        result_news_sports_pt = await dummy_gem.command_executor.execute(
            "get_news", category="sports", language="pt", page_size=1
        )
        print(result_news_sports_pt["output"])
        assert result_news_sports_pt["success"] is True
        assert "Benfica Vence Clássico com Golo no Último Minuto" in result_news_sports_pt["output"]

        # --- Teste 3: Obter Notícias Sem Resultados ---
        print("\n--- Teste 3: Obter Notícias Sem Resultados ---")
        result_no_news = await dummy_gem.command_executor.execute(
            "get_news", query="consulta sem resultados"
        )
        print(result_no_news["output"])
        assert result_no_news["success"] is True
        assert "Não foram encontrados artigos de notícias com os critérios especificados." in result_no_news["output"]

        # --- Teste 4: Simular Erro de API ---
        print("\n--- Teste 4: Simular Erro de API ---")
        result_api_error = await dummy_gem.command_executor.execute(
            "get_news", query="erro api"
        )
        print(result_api_error["output"])
        assert result_api_error["success"] is False
        assert "Desculpe, houve um erro ao buscar notícias: 403." in dummy_gem.notification_manager._history[-1]["message"]


        print("\n--- Testes do NewsManager concluídos com sucesso. ---")
        await news_manager.shutdown()
        
        # Restore original httpx.AsyncClient.get
        httpx.AsyncClient.get = original_httpx_get

    asyncio.run(run_news_manager_tests())

