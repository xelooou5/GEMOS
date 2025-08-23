#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
üíé GEM OS - Social Media Manager (core/social_media_manager.py)
Manages interactions with social media platforms, including posting updates and reading feeds.

Responsibilities
----------------
- Post updates/content to configured social media platforms.
- Retrieve posts/news from social media feeds.
- Securely manage platform credentials (API keys, access tokens).
- Expose social media capabilities as tools for the LLM.
- Publish social media-related events.
- Integrate with NotificationManager for alerts.
"""

from __future__ import annotations

import asyncio
import logging
import httpx # Para requisi√ß√µes HTTP ass√≠ncronas
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable, Awaitable

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

# --- Dataclass para Postagem de M√≠dia Social ---
@dataclass
class SocialMediaPost:
    platform: str
    post_id: str
    author: str
    content: str
    timestamp: datetime
    url: Optional[str] = None
    media_url: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "platform": self.platform,
            "post_id": self.post_id,
            "author": self.author,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "url": self.url,
            "media_url": self.media_url,
        }

# --- Social Media Manager como um Plugin ---
class SocialMediaManager(BasePlugin):
    """
    Manages social media interactions for GEM OS, acting as a plugin.
    This implementation uses mock APIs for demonstration. Real integration would
    require specific SDKs and full OAuth flows for each platform.
    """
    def __init__(self, gem_instance: GEMVoiceAssistant, logger: Optional[logging.Logger] = None):
        super().__init__(gem_instance, logger)
        self.logger.info("SocialMediaManager plugin inicializado.")
        
        self.event_manager: EventManager = gem_instance.event_manager
        self.notification_manager: NotificationManager = gem_instance.notification_manager
        self.tts_module: TTSModule = gem_instance.tts_module
        self.config_manager: ConfigManager = gem_instance.config_manager

        # Mock API URLs (in a real scenario, these would be actual platform APIs)
        self._mock_twitter_api_url = "https://api.mocktwitter.com/v1"
        self._mock_facebook_api_url = "https://api.mockfacebook.com/v1"
        self._mock_instagram_api_url = "https://api.mockinstagram.com/v1"

        # Mock API keys/tokens (in a real scenario, fetched securely from CredentialManager)
        self._twitter_api_key = os.getenv("TWITTER_API_KEY", "MOCK_TWITTER_KEY")
        self._facebook_api_token = os.getenv("FACEBOOK_API_TOKEN", "MOCK_FACEBOOK_TOKEN")
        self._instagram_api_token = os.getenv("INSTAGRAM_API_TOKEN", "MOCK_INSTAGRAM_TOKEN")

        self._http_client = httpx.AsyncClient()

        if self._twitter_api_key == "MOCK_TWITTER_KEY" or \
           self._facebook_api_token == "MOCK_FACEBOOK_TOKEN" or \
           self._instagram_api_token == "MOCK_INSTAGRAM_TOKEN":
            self.logger.warning("Credenciais de m√≠dia social est√£o usando valores de MOCK. Funcionalidade real ser√° limitada.")
        
        self.logger.info("SocialMediaManager configurado com APIs mock.")

    async def initialize(self) -> None:
        """Performs any necessary setup for the social media manager."""
        self.event_manager.subscribe("GEM_SHUTDOWN", self._on_gem_shutdown)
        self.logger.info("SocialMediaManager inicializado.")

    async def _on_gem_shutdown(self, event_data: Dict[str, Any]) -> None:
        """Handler for GEM_SHUTDOWN event to gracefully close HTTP client."""
        self.logger.info("Recebido GEM_SHUTDOWN. A fechar cliente HTTP do SocialMediaManager.")
        await self.shutdown()

    async def _post_update_to_platform(self, platform: str, message: str,
                                       media_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Simulates posting an update to a social media platform.
        In a real implementation, this would call the specific platform's API.
        """
        api_url = None
        headers = {}
        if platform.lower() == "twitter":
            api_url = f"{self._mock_twitter_api_url}/tweets"
            headers["Authorization"] = f"Bearer {self._twitter_api_key}"
        elif platform.lower() == "facebook":
            api_url = f"{self._mock_facebook_api_url}/posts"
            headers["Authorization"] = f"Bearer {self._facebook_api_token}"
        elif platform.lower() == "instagram":
            api_url = f"{self._mock_instagram_api_url}/media"
            headers["Authorization"] = f"Bearer {self._instagram_api_token}"
        else:
            return {"success": False, "output": "", "error": f"Plataforma '{platform}' n√£o suportada."}
        
        if "MOCK" in headers.get("Authorization", ""):
            self.logger.warning(f"Usando credenciais mock para {platform}. Postagem apenas simulada.")
            await asyncio.sleep(0.5) # Simulate API call delay
            post_id = f"mock-post-{datetime.now().timestamp()}"
            await self.notification_manager.add_notification(
                f"Postagem simulada para {platform}: '{message[:50]}...' (ID: {post_id}).", level=NOTIFICATION_INFO
            )
            await self.event_manager.publish("SOCIAL_MEDIA_POSTED_MOCK", {
                "platform": platform, "message": message, "media_url": media_url, "post_id": post_id
            })
            return {"success": True, "output": f"Postagem simulada para {platform} criada com ID: {post_id}", "error": None}


        payload = {"text": message}
        if media_url:
            payload["media_url"] = media_url # This would be platform specific

        self.logger.info(f"Simulando postagem para {platform}...")
        try:
            response = await self._http_client.post(api_url, json=payload, headers=headers, timeout=10.0)
            response.raise_for_status()
            data = response.json()
            
            post_id = data.get("id", "unknown")
            message = f"Postagem para {platform} criada com sucesso. ID: {post_id}"
            await self.notification_manager.add_notification(message, level=NOTIFICATION_SUCCESS)
            await self.tts_module.speak(message)
            await self.event_manager.publish("SOCIAL_MEDIA_POSTED", {
                "platform": platform, "message": message, "media_url": media_url, "post_id": post_id
            })
            return {"success": True, "output": message, "error": None}

        except httpx.HTTPStatusError as e:
            error_msg = f"Erro HTTP ao postar para {platform}: {e.response.status_code} - {e.response.text}"
            self.logger.error(error_msg, exc_info=True)
            await self.notification_manager.add_notification(f"Falha ao postar em {platform}: {e.response.status_code}", level=NOTIFICATION_ERROR)
            await self.tts_module.speak(f"Desculpe, houve um erro ao postar em {platform}.")
            return {"success": False, "output": "", "error": error_msg}
        except httpx.RequestError as e:
            error_msg = f"Erro de rede/requisi√ß√£o ao postar para {platform}: {e}"
            self.logger.error(error_msg, exc_info=True)
            await self.notification_manager.add_notification(f"Erro de rede ao postar em {platform}.", level=NOTIFICATION_ERROR)
            await self.tts_module.speak(f"Desculpe, houve um problema de rede ao postar em {platform}.")
            return {"success": False, "output": "", "error": error_msg}
        except Exception as e:
            error_msg = f"Erro inesperado ao postar para {platform}: {e}"
            self.logger.error(error_msg, exc_info=True)
            await self.notification_manager.add_notification(f"Erro inesperado ao postar em {platform}.", level=NOTIFICATION_ERROR)
            await self.tts_module.speak(f"Desculpe, ocorreu um erro inesperado ao postar em {platform}.")
            return {"success": False, "output": "", "error": error_msg}

    async def _get_feed_from_platform(self, platform: str, limit: int = 3) -> List[SocialMediaPost]:
        """
        Simulates retrieving a feed from a social media platform.
        """
        api_url = None
        headers = {}
        if platform.lower() == "twitter":
            api_url = f"{self._mock_twitter_api_url}/home_timeline"
            headers["Authorization"] = f"Bearer {self._twitter_api_key}"
        elif platform.lower() == "facebook":
            api_url = f"{self._mock_facebook_api_url}/feed"
            headers["Authorization"] = f"Bearer {self._facebook_api_token}"
        elif platform.lower() == "instagram":
            api_url = f"{self._mock_instagram_api_url}/user_feed"
            headers["Authorization"] = f"Bearer {self._instagram_api_token}"
        else:
            self.logger.warning(f"Plataforma '{platform}' n√£o suportada para obter feed.")
            return []

        if "MOCK" in headers.get("Authorization", ""):
            self.logger.warning(f"Usando credenciais mock para {platform}. Obten√ß√£o de feed apenas simulada.")
            await asyncio.sleep(0.5)
            mock_posts = [
                SocialMediaPost(platform=platform, post_id="mock-1", author="MockUser1", content="Primeira postagem mock.", timestamp=datetime.now() - timedelta(minutes=10)),
                SocialMediaPost(platform=platform, post_id="mock-2", author="MockUser2", content="Segunda postagem mock, com #hashtags.", timestamp=datetime.now() - timedelta(minutes=20)),
                SocialMediaPost(platform=platform, post_id="mock-3", author="MockUser1", content="Terceira postagem.", timestamp=datetime.now() - timedelta(minutes=30)),
            ]
            await self.notification_manager.add_notification(
                f"Feed simulado obtido para {platform}.", level=NOTIFICATION_INFO
            )
            return mock_posts[:limit]

        self.logger.info(f"Simulando obten√ß√£o de feed para {platform}...")
        try:
            response = await self._http_client.get(api_url, headers=headers, params={"limit": limit}, timeout=10.0)
            response.raise_for_status()
            data = response.json()

            posts: List[SocialMediaPost] = []
            for item in data.get("posts", []): # Assuming a 'posts' key in API response
                if all([item.get("id"), item.get("author"), item.get("content"), item.get("timestamp")]):
                    posts.append(SocialMediaPost(
                        platform=platform,
                        post_id=item["id"],
                        author=item["author"],
                        content=item["content"],
                        timestamp=datetime.fromisoformat(item["timestamp"]),
                        url=item.get("url"),
                        media_url=item.get("media_url")
                    ))
            
            await self.notification_manager.add_notification(
                f"Feed de {platform} obtido. {len(posts)} posts.", level=NOTIFICATION_SUCCESS, vocalize=False
            )
            await self.event_manager.publish("SOCIAL_MEDIA_FEED_RETRIEVED", {"platform": platform, "posts_count": len(posts)})
            return posts

        except httpx.HTTPStatusError as e:
            error_msg = f"Erro HTTP ao obter feed de {platform}: {e.response.status_code} - {e.response.text}"
            self.logger.error(error_msg, exc_info=True)
            await self.notification_manager.add_notification(f"Falha ao obter feed de {platform}: {e.response.status_code}", level=NOTIFICATION_ERROR)
            await self.tts_module.speak(f"Desculpe, houve um erro ao obter o feed de {platform}.")
            return []
        except httpx.RequestError as e:
            error_msg = f"Erro de rede/requisi√ß√£o ao obter feed de {platform}: {e}"
            self.logger.error(error_msg, exc_info=True)
            await self.notification_manager.add_notification(f"Erro de rede ao obter feed de {platform}.", level=NOTIFICATION_ERROR)
            await self.tts_module.speak(f"Desculpe, houve um problema de rede ao obter o feed de {platform}.")
            return []
        except Exception as e:
            error_msg = f"Erro inesperado ao obter feed de {platform}: {e}"
            self.logger.error(error_msg, exc_info=True)
            await self.notification_manager.add_notification(f"Erro inesperado ao obter feed de {platform}.", level=NOTIFICATION_ERROR)
            await self.tts_module.speak(f"Desculpe, ocorreu um erro inesperado ao obter o feed de {platform}.")
            return []


    # --------------------------------------------------------------------- Commands

    async def _post_social_update_command(self, platform: str, message: str, media_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Posta uma atualiza√ß√£o de texto ou com m√≠dia para uma plataforma de m√≠dia social.
        Plataformas suportadas: "twitter", "facebook", "instagram".
        """
        if not message:
            return {"success": False, "output": "", "error": "A mensagem n√£o pode estar vazia."}
        
        platforms_supported = ["twitter", "facebook", "instagram"]
        if platform.lower() not in platforms_supported:
            await self._speak_response(f"Plataforma de m√≠dia social '{platform}' n√£o suportada. Tente: {', '.join(platforms_supported)}.")
            return {"success": False, "output": "", "error": f"Plataforma '{platform}' n√£o suportada."}

        result = await self._post_update_to_platform(platform, message, media_url)
        if result["success"]:
            output_message = f"Postagem para {platform} conclu√≠da: {result['output']}"
            await self._speak_response(f"A sua postagem para {platform} foi enviada.")
            return {"success": True, "output": output_message, "error": None}
        else:
            await self._speak_response(f"N√£o foi poss√≠vel postar em {platform}. Verifique os logs.")
            return result # Pass through error

    async def _get_social_feed_command(self, platform: str, limit: int = 3) -> Dict[str, Any]:
        """
        Obt√©m e apresenta o feed de not√≠cias ou postagens de uma plataforma de m√≠dia social.
        Plataformas suportadas: "twitter", "facebook", "instagram".
        """
        platforms_supported = ["twitter", "facebook", "instagram"]
        if platform.lower() not in platforms_supported:
            await self._speak_response(f"Plataforma de m√≠dia social '{platform}' n√£o suportada para feed. Tente: {', '.join(platforms_supported)}.")
            return {"success": False, "output": "", "error": f"Plataforma '{platform}' n√£o suportada."}

        if not (1 <= limit <= 10):
            return {"success": False, "output": "", "error": "O limite de posts deve ser entre 1 e 10."}

        posts = await self._get_feed_from_platform(platform, limit)

        if not posts:
            message = f"N√£o foram encontrados posts no feed de {platform}."
            await self._speak_response(message)
            return {"success": True, "output": message, "error": None}

        output_lines = [f"Feed de {platform} (√∫ltimos {len(posts)} posts):"]
        for i, post in enumerate(posts):
            output_lines.append(f"{i+1}. De: {post.author} (em {post.timestamp.strftime('%Y-%m-%d %H:%M')})")
            output_lines.append(f"   Conte√∫do: {post.content}")
            if post.url:
                output_lines.append(f"   URL: {post.url}")
            output_lines.append("-" * 20)
        
        message = "\n".join(output_lines)
        await self._speak_response(f"O feed de {platform} foi obtido. Verifique o ecr√£ para os posts mais recentes.")
        return {"success": True, "output": message, "error": None}


    # --------------------------------------------------------------------- Plugin Interface

    def register_commands(self, executor: CommandExecutor) -> None:
        """Registers social media management commands with the CommandExecutor."""
        self.logger.info("A registar comandos do plugin SocialMediaManager...")
        executor.register_command("post_social_update", self._post_social_update_command)
        executor.register_command("get_social_feed", self._get_social_feed_command)
        self.logger.info("Comandos SocialMediaManager registados.")

    def get_tools_schema(self) -> List[Dict[str, Any]]:
        """
        Returns a list of tool definitions (schemas) for social media features.
        These schemas are exposed to the LLM for function calling.
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": "post_social_update",
                    "description": "Posta uma atualiza√ß√£o de texto ou com m√≠dia (opcional) em uma plataforma de m√≠dia social configurada (Twitter, Facebook, Instagram). Requer a plataforma e a mensagem.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "platform": {
                                "type": "string",
                                "description": "A plataforma de m√≠dia social para postar (ex: 'twitter', 'facebook', 'instagram').",
                                "enum": ["twitter", "facebook", "instagram"]
                            },
                            "message": {
                                "type": "string",
                                "description": "O conte√∫do da mensagem a ser postada.",
                            },
                            "media_url": {
                                "type": "string",
                                "description": "Um URL para anexar m√≠dia (imagem/v√≠deo) √† postagem. Opcional.",
                            }
                        },
                        "required": ["platform", "message"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_social_feed",
                    "description": "Obt√©m os posts mais recentes do feed de uma plataforma de m√≠dia social configurada (Twitter, Facebook, Instagram).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "platform": {
                                "type": "string",
                                "description": "A plataforma de m√≠dia social da qual obter o feed (ex: 'twitter', 'facebook', 'instagram').",
                                "enum": ["twitter", "facebook", "instagram"]
                            },
                            "limit": {
                                "type": "integer",
                                "description": "O n√∫mero m√°ximo de posts a retornar. Padr√£o para 3, m√°ximo de 10.",
                                "default": 3,
                                "minimum": 1,
                                "maximum": 10
                            }
                        },
                        "required": ["platform"],
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
        self.logger.info("SocialMediaManager a ser desligado. A fechar o cliente HTTP.")
        if self._http_client:
            await self._http_client.aclose()
        self.event_manager.unsubscribe("GEM_SHUTDOWN", self._on_gem_shutdown)


# =============================================================================
# CLI Test
# =============================================================================

if __name__ == "__main__":
    import asyncio
    import json
    
    # Configure logging for standalone test
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger("TestSocialMediaManager")

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
                    'twitter_api_key': "MOCK_TWITTER_KEY",
                    'facebook_api_token': "MOCK_FACEBOOK_TOKEN",
                    'instagram_api_token': "MOCK_INSTAGRAM_TOKEN",
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

    # Mock the httpx.AsyncClient for testing without real API calls
    async def mock_httpx_post(*args, **kwargs):
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

        platform = ""
        if "twitter" in args[0].lower(): platform = "twitter"
        elif "facebook" in args[0].lower(): platform = "facebook"
        elif "instagram" in args[0].lower(): platform = "instagram"

        if "MOCK" in kwargs.get("headers", {}).get("Authorization", ""):
            logger.info(f"Mocking POST for {platform} with MOCK credentials.")
            return MockResponse(200, {"id": f"mock-post-{platform}-{datetime.now().timestamp()}"})
        else:
            logger.info(f"Simulating real POST for {platform}.")
            return MockResponse(200, {"id": f"real-post-{platform}-{datetime.now().timestamp()}"})

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
        
        platform = ""
        if "twitter" in args[0].lower(): platform = "twitter"
        elif "facebook" in args[0].lower(): platform = "facebook"
        elif "instagram" in args[0].lower(): platform = "instagram"

        if "MOCK" in kwargs.get("headers", {}).get("Authorization", ""):
            logger.info(f"Mocking GET for {platform} with MOCK credentials.")
            return MockResponse(200, {
                "posts": [
                    {"id": "mock-1", "author": "UserA", "content": "Hello from Mock!", "timestamp": "2025-08-22T10:00:00Z"},
                    {"id": "mock-2", "author": "UserB", "content": "Nice weather today.", "timestamp": "2025-08-22T09:30:00Z"},
                ]
            })
        else:
            logger.info(f"Simulating real GET for {platform}.")
            return MockResponse(200, {
                "posts": [
                    {"id": "real-1", "author": "RealUser1", "content": "Real post 1!", "timestamp": "2025-08-22T11:00:00Z"},
                ]
            })

    # Patch httpx.AsyncClient methods with our mocks for testing
    original_httpx_post = httpx.AsyncClient.post
    original_httpx_get = httpx.AsyncClient.get
    httpx.AsyncClient.post = mock_httpx_post
    httpx.AsyncClient.get = mock_httpx_get

    async def run_social_media_manager_tests():
        print("\n--- Iniciando Testes do SocialMediaManager ---")

        dummy_gem = DummyGEM(logger)
        social_media_manager = SocialMediaManager(dummy_gem, logger)
        
        social_media_manager.register_commands(dummy_gem.command_executor)

        await social_media_manager.initialize()

        # --- Teste 1: Postar Atualiza√ß√£o no Twitter (Mock) ---
        print("\n--- Teste 1: Postar Atualiza√ß√£o no Twitter (Mock) ---")
        result_post_twitter = await dummy_gem.command_executor.execute(
            "post_social_update", platform="twitter", message="Ol√°, GEM OS est√° online!"
        )
        print(result_post_twitter["output"])
        assert result_post_twitter["success"] is True
        assert "Postagem simulada para twitter criada com ID: mock-post-twitter-" in result_post_twitter["output"]

        # --- Teste 2: Obter Feed do Facebook (Mock) ---
        print("\n--- Teste 2: Obter Feed do Facebook (Mock) ---")
        result_get_feed_facebook = await dummy_gem.command_executor.execute(
            "get_social_feed", platform="facebook", limit=1
        )
        print(result_get_feed_facebook["output"])
        assert result_get_feed_facebook["success"] is True
        assert "Feed de facebook (√∫ltimos 1 posts):" in result_get_feed_facebook["output"]
        assert "De: MockUser1" in result_get_feed_facebook["output"]

        # --- Teste 3: Tentar Postar em Plataforma N√£o Suportada ---
        print("\n--- Teste 3: Tentar Postar em Plataforma N√£o Suportada ---")
        result_post_invalid = await dummy_gem.command_executor.execute(
            "post_social_update", platform="linkedin", message="Isto n√£o deve funcionar."
        )
        print(result_post_invalid["output"])
        assert result_post_invalid["success"] is False
        assert "Plataforma 'linkedin' n√£o suportada." in result_post_invalid["error"]

        # --- Teste 4: Tentar Postar Mensagem Vazia ---
        print("\n--- Teste 4: Tentar Postar Mensagem Vazia ---")
        result_post_empty = await dummy_gem.command_executor.execute(
            "post_social_update", platform="twitter", message=""
        )
        print(result_post_empty["output"])
        assert result_post_empty["success"] is False
        assert "A mensagem n√£o pode estar vazia." in result_post_empty["error"]

        # --- Teste 5: Postar com M√≠dia (Mock) ---
        print("\n--- Teste 5: Postar com M√≠dia (Mock) ---")
        result_post_media = await dummy_gem.command_executor.execute(
            "post_social_update", platform="instagram", message="Nova foto do p√¥r do sol!", media_url="https://example.com/sunset.jpg"
        )
        print(result_post_media["output"])
        assert result_post_media["success"] is True
        assert "Postagem simulada para instagram: 'Nova foto do p√¥r do sol!'..." in dummy_gem.notification_manager._history[-1]["message"]


        print("\n--- Testes do SocialMediaManager conclu√≠dos com sucesso. ---")
        await social_media_manager.shutdown()
        
        # Restore original httpx.AsyncClient methods
        httpx.AsyncClient.post = original_httpx_post
        httpx.AsyncClient.get = original_httpx_get

    asyncio.run(run_social_media_manager_tests())

