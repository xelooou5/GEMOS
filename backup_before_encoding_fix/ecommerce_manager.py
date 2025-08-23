#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
💎 GEM OS - E-commerce Manager (core/ecommerce_manager.py)
Manages e-commerce related tasks, including product search, price comparison, and wishlist management.

Responsibilities
----------------
- Search for products using mock e-commerce APIs.
- Manage a user's wishlist (add, list, remove items).
- Expose e-commerce capabilities as tools for the LLM.
- Publish e-commerce related events.
- Integrate with NotificationManager for alerts.
"""

from __future__ import annotations

import asyncio
import logging
import httpx # Para requisições HTTP assíncronas
import uuid
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

class Storage:
    async def get_setting(self, key: str, default: Any = None) -> Any:
        pass
    async def set_setting(self, key: str, value: Any) -> bool:
        pass

# --- Dataclass para Produto ---
@dataclass
class Product:
    id: str
    name: str
    price: float
    currency: str
    store: str
    url: Optional[str] = None
    image_url: Optional[str] = None
    description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "price": self.price,
            "currency": self.currency,
            "store": self.store,
            "url": self.url,
            "image_url": self.image_url,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Product:
        return cls(
            id=data["id"],
            name=data["name"],
            price=data["price"],
            currency=data["currency"],
            store=data["store"],
            url=data.get("url"),
            image_url=data.get("image_url"),
            description=data.get("description"),
        )

# --- E-commerce Manager como um Plugin ---
class EcommerceManager(BasePlugin):
    """
    Manages e-commerce related tasks for GEM OS, acting as a plugin.
    This implementation uses mock APIs and local storage for demonstration.
    Real integration would require actual e-commerce APIs (e.g., Amazon, Mercado Livre)
    and robust authentication.
    """
    STORAGE_KEY_WISHLIST = "user_ecommerce_wishlist"
    
    def __init__(self, gem_instance: GEMVoiceAssistant, logger: Optional[logging.Logger] = None):
        super().__init__(gem_instance, logger)
        self.logger.info("EcommerceManager plugin inicializado.")
        
        self.event_manager: EventManager = gem_instance.event_manager
        self.notification_manager: NotificationManager = gem_instance.notification_manager
        self.storage: Storage = gem_instance.storage
        self.tts_module: TTSModule = gem_instance.tts_module
        self.config_manager: ConfigManager = gem_instance.config_manager

        self._http_client = httpx.AsyncClient()
        self._wishlist: Dict[str, Product] = {} # {product_id: Product_object}
        self._wishlist_loaded = asyncio.Event()

        # Mock API URL (in a real scenario, this would be an actual e-commerce API)
        self._mock_ecommerce_api_url = "https://api.mockecommerce.com/v1"
        self._mock_api_key = os.getenv("ECOMMERCE_API_KEY", "MOCK_ECOMMERCE_KEY")

        if self._mock_api_key == "MOCK_ECOMMERCE_KEY":
            self.logger.warning("Credenciais de e-commerce estão usando valores de MOCK. Funcionalidade real será limitada.")
        
        self.logger.info("EcommerceManager configurado com APIs mock.")

    async def initialize(self) -> None:
        """Loads wishlist from storage and performs any necessary setup."""
        await self._load_wishlist_from_storage()
        self.event_manager.subscribe("GEM_SHUTDOWN", self._on_gem_shutdown)
        self.logger.info("EcommerceManager inicializado.")

    async def _on_gem_shutdown(self, event_data: Dict[str, Any]) -> None:
        """Handler for GEM_SHUTDOWN event to gracefully close HTTP client."""
        self.logger.info("Recebido GEM_SHUTDOWN. A fechar cliente HTTP do EcommerceManager.")
        await self.shutdown()

    async def _load_wishlist_from_storage(self) -> None:
        """Loads wishlist items from persistent storage."""
        try:
            wishlist_data = await self.storage.get_setting(self.STORAGE_KEY_WISHLIST, [])
            for product_dict in wishlist_data:
                try:
                    product = Product.from_dict(product_dict)
                    self._wishlist[product.id] = product
                except Exception as e:
                    self.logger.error(f"Erro ao carregar item da lista de desejos: {e} - Dados: {product_dict}", exc_info=True)
            self.logger.info(f"Carregados {len(self._wishlist)} itens da lista de desejos do armazenamento.")
        except Exception as e:
            self.logger.error(f"Falha ao carregar lista de desejos do armazenamento: {e}", exc_info=True)
        finally:
            self._wishlist_loaded.set() # Sinaliza que a wishlist foi carregada

    async def _save_wishlist_to_storage(self) -> None:
        """Saves current wishlist items to persistent storage."""
        try:
            wishlist_data = [product.to_dict() for product in self._wishlist.values()]
            await self.storage.set_setting(self.STORAGE_KEY_WISHLIST, wishlist_data)
            self.logger.debug(f"Salvos {len(self._wishlist)} itens na lista de desejos para o armazenamento.")
        except Exception as e:
            self.logger.error(f"Falha ao salvar lista de desejos no armazenamento: {e}", exc_info=True)

    async def _search_products_api(self, query: str, limit: int = 3) -> List[Product]:
        """
        Simulates searching for products using an e-commerce API.
        """
        search_url = f"{self._mock_ecommerce_api_url}/products/search"
        headers = {"Authorization": f"Bearer {self._mock_api_key}"}
        params = {"q": query, "limit": limit}

        if "MOCK_ECOMMERCE_KEY" in self._mock_api_key:
            self.logger.warning(f"Usando credenciais mock para e-commerce. Busca de produtos apenas simulada.")
            await asyncio.sleep(0.5) # Simulate API call delay
            if "smartphone" in query.lower():
                mock_products = [
                    Product(id="prod-101", name="Smartphone X", price=1200.00, currency="BRL", store="LojaTech", url="https://loja.tech/smartphone-x"),
                    Product(id="prod-102", name="Smartphone Y Pro", price=1800.00, currency="BRL", store="MegaEletronicos", url="https://megaeletronicos.com/smartphone-y"),
                ]
            elif "livro" in query.lower():
                mock_products = [
                    Product(id="book-201", name="Dom Quixote", price=50.00, currency="BRL", store="LivrariaDigital", url="https://livrariadigital.com/dom-quixote"),
                ]
            else:
                mock_products = []
            
            await self.notification_manager.add_notification(
                f"Busca simulada de produtos para '{query}' concluída.", level=NOTIFICATION_INFO
            )
            return mock_products[:limit]


        self.logger.info(f"Simulando busca de produtos para '{query}' com limite {limit}...")
        try:
            response = await self._http_client.get(search_url, params=params, headers=headers, timeout=10.0)
            response.raise_for_status()
            data = response.json()

            products: List[Product] = []
            for item in data.get("products", []):
                if all([item.get("id"), item.get("name"), item.get("price"), item.get("currency"), item.get("store")]):
                    products.append(Product(
                        id=item["id"],
                        name=item["name"],
                        price=item["price"],
                        currency=item["currency"],
                        store=item["store"],
                        url=item.get("url"),
                        image_url=item.get("image_url"),
                        description=item.get("description")
                    ))
            
            await self.notification_manager.add_notification(
                f"Busca de produtos para '{query}' concluída. {len(products)} resultados.", level=NOTIFICATION_SUCCESS, vocalize=False
            )
            await self.event_manager.publish("ECOMMERCE_PRODUCT_SEARCHED", {"query": query, "results_count": len(products)})
            return products

        except httpx.HTTPStatusError as e:
            error_msg = f"Erro HTTP ao buscar produtos: {e.response.status_code} - {e.response.text}"
            self.logger.error(error_msg, exc_info=True)
            await self.notification_manager.add_notification(f"Falha na busca de produtos: {e.response.status_code}", level=NOTIFICATION_ERROR)
            await self.tts_module.speak(f"Desculpe, houve um erro ao buscar produtos.")
            return []
        except httpx.RequestError as e:
            error_msg = f"Erro de rede/requisição ao buscar produtos: {e}"
            self.logger.error(error_msg, exc_info=True)
            await self.notification_manager.add_notification(f"Erro de rede na busca de produtos.", level=NOTIFICATION_ERROR)
            await self.tts_module.speak(f"Desculpe, houve um problema de rede ao buscar produtos.")
            return []
        except Exception as e:
            error_msg = f"Erro inesperado ao buscar produtos: {e}"
            self.logger.error(error_msg, exc_info=True)
            await self.notification_manager.add_notification(f"Erro inesperado na busca de produtos.", level=NOTIFICATION_ERROR)
            await self.tts_module.speak(f"Desculpe, ocorreu um erro inesperado ao buscar produtos.")
            return []

    # --------------------------------------------------------------------- Commands

    async def _search_products_command(self, query: str, limit: int = 3) -> Dict[str, Any]:
        """
        Pesquisa produtos em lojas online com base em uma consulta.
        """
        if not query:
            return {"success": False, "output": "", "error": "A consulta de pesquisa não pode estar vazia."}
        
        if not (1 <= limit <= 10):
            return {"success": False, "output": "", "error": "O limite de produtos deve ser entre 1 e 10."}

        products = await self._search_products_api(query, limit)

        if not products:
            message = f"Não foram encontrados produtos para a pesquisa: '{query}'."
            await self._speak_response(message)
            return {"success": True, "output": message, "error": None}
        
        output_lines = [f"Resultados da pesquisa para '{query}':"]
        for i, product in enumerate(products):
            output_lines.append(f"{i+1}. {product.name} - Preço: {product.price:.2f} {product.currency} na {product.store}")
            if product.url:
                output_lines.append(f"   URL: {product.url}")
            output_lines.append("-" * 20)
        
        message = "\n".join(output_lines)
        await self._speak_response(f"Produtos encontrados para '{query}'. Verifique o ecrã para os detalhes.")
        return {"success": True, "output": message, "error": None}

    async def _add_to_wishlist_command(self, product_name: str, price: float, currency: str, store: str,
                                      url: Optional[str] = None, image_url: Optional[str] = None,
                                      description: Optional[str] = None) -> Dict[str, Any]:
        """
        Adiciona um produto à lista de desejos do usuário.
        """
        await self._wishlist_loaded.wait()

        product_id = str(uuid.uuid4())
        new_product = Product(
            id=product_id,
            name=product_name,
            price=price,
            currency=currency,
            store=store,
            url=url,
            image_url=image_url,
            description=description
        )
        self._wishlist[product_id] = new_product
        await self._save_wishlist_to_storage()

        message = f"'{product_name}' adicionado à sua lista de desejos."
        await self._speak_response(message)
        await self.notification_manager.add_notification(message, level=NOTIFICATION_SUCCESS)
        await self.event_manager.publish("ECOMMERCE_WISHLIST_ADDED", new_product.to_dict())
        self.logger.info(message)
        return {"success": True, "output": message, "error": None}

    async def _list_wishlist_command(self) -> Dict[str, Any]:
        """
        Lista todos os itens na lista de desejos do usuário.
        """
        await self._wishlist_loaded.wait()

        if not self._wishlist:
            message = "A sua lista de desejos está vazia."
            await self._speak_response(message)
            return {"success": True, "output": message, "error": None}
        
        output_lines = ["Sua lista de desejos:"]
        for i, product in enumerate(self._wishlist.values()):
            output_lines.append(f"{i+1}. {product.name} - {product.price:.2f} {product.currency} na {product.store}")
            if product.url:
                output_lines.append(f"   URL: {product.url}")
            output_lines.append(f"   (ID: {product.id[:8]}...)")
            output_lines.append("-" * 20)
        
        message = "\n".join(output_lines)
        await self._speak_response(f"Sua lista de desejos foi listada. Verifique o ecrã para os detalhes.")
        await self.notification_manager.add_notification("Lista de desejos exibida.", level=NOTIFICATION_INFO)
        return {"success": True, "output": message, "error": None}

    async def _remove_from_wishlist_command(self, product_id_prefix: str) -> Dict[str, Any]:
        """
        Remove um produto da lista de desejos.
        Requer um prefixo do ID do produto.
        """
        await self._wishlist_loaded.wait()

        product_to_remove: Optional[Product] = None
        matching_products = [p for p in self._wishlist.values() if p.id.startswith(product_id_prefix)]

        if len(matching_products) == 1:
            product_to_remove = matching_products[0]
        elif len(matching_products) > 1:
            message = f"Múltiplos produtos correspondem ao ID '{product_id_prefix}'. Por favor, seja mais específico."
            await self._speak_response(message)
            return {"success": False, "output": message, "error": "Multiple matches"}
        else:
            message = f"Nenhum produto encontrado com o ID '{product_id_prefix}' na sua lista de desejos."
            await self._speak_response(message)
            return {"success": False, "output": message, "error": "Product not found"}

        if product_to_remove:
            del self._wishlist[product_to_remove.id]
            await self._save_wishlist_to_storage()
            message = f"'{product_to_remove.name}' (ID: {product_to_remove.id[:8]}...) removido da sua lista de desejos."
            await self._speak_response(message)
            await self.notification_manager.add_notification(message, level=NOTIFICATION_SUCCESS)
            await self.event_manager.publish("ECOMMERCE_WISHLIST_REMOVED", {"product_id": product_to_remove.id})
            self.logger.info(message)
            return {"success": True, "output": message, "error": None}
        
        return {"success": False, "output": "Erro desconhecido ao remover produto da lista de desejos.", "error": "Unknown error"}

    # --------------------------------------------------------------------- Plugin Interface

    def register_commands(self, executor: CommandExecutor) -> None:
        """Registers e-commerce management commands with the CommandExecutor."""
        self.logger.info("A registar comandos do plugin EcommerceManager...")
        executor.register_command("search_products", self._search_products_command)
        executor.register_command("add_to_wishlist", self._add_to_wishlist_command)
        executor.register_command("list_wishlist", self._list_wishlist_command)
        executor.register_command("remove_from_wishlist", self._remove_from_wishlist_command)
        self.logger.info("Comandos EcommerceManager registados.")

    def get_tools_schema(self) -> List[Dict[str, Any]]:
        """
        Returns a list of tool definitions (schemas) for e-commerce features.
        These schemas are exposed to the LLM for function calling.
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": "search_products",
                    "description": "Pesquisa produtos em lojas online com base em uma consulta de texto. Retorna os detalhes dos produtos encontrados, incluindo nome, preço, loja e URL. Limitado a 10 resultados.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "A consulta de pesquisa para os produtos (ex: 'smartphone', 'livro de ficção científica').",
                            },
                            "limit": {
                                "type": "integer",
                                "description": "O número máximo de produtos a retornar. Padrão para 3, máximo de 10.",
                                "default": 3,
                                "minimum": 1,
                                "maximum": 10
                            }
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "add_to_wishlist",
                    "description": "Adiciona um produto à lista de desejos do usuário. Requer o nome do produto, preço, moeda e a loja onde foi encontrado. Opcionalmente, pode incluir URL e descrição.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "product_name": {
                                "type": "string",
                                "description": "O nome do produto a ser adicionado à lista de desejos.",
                            },
                            "price": {
                                "type": "number",
                                "format": "float",
                                "description": "O preço do produto.",
                            },
                            "currency": {
                                "type": "string",
                                "description": "A moeda do preço (ex: 'BRL', 'USD').",
                            },
                            "store": {
                                "type": "string",
                                "description": "O nome da loja onde o produto foi encontrado.",
                            },
                            "url": {
                                "type": "string",
                                "description": "O URL para a página do produto. Opcional.",
                            },
                            "image_url": {
                                "type": "string",
                                "description": "O URL de uma imagem do produto. Opcional.",
                            },
                            "description": {
                                "type": "string",
                                "description": "Uma breve descrição do produto. Opcional.",
                            }
                        },
                        "required": ["product_name", "price", "currency", "store"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "list_wishlist",
                    "description": "Lista todos os produtos que estão atualmente na lista de desejos do usuário, mostrando seus detalhes como nome, preço e loja.",
                    "parameters": {"type": "object", "properties": {}, "required": []},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "remove_from_wishlist",
                    "description": "Remove um produto da lista de desejos do usuário. Requer o ID completo ou um prefixo único do produto.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "product_id_prefix": {
                                "type": "string",
                                "description": "O ID completo ou um prefixo único do produto a ser removido da lista de desejos.",
                            },
                        },
                        "required": ["product_id_prefix"],
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
        self.logger.info("EcommerceManager a ser desligado. A fechar o cliente HTTP.")
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
    logger = logging.getLogger("TestEcommerceManager")

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
                    'ecommerce_api_key': "MOCK_ECOMMERCE_KEY",
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

    # Mock the httpx.AsyncClient for testing without real API calls
    async def mock_httpx_get_ecommerce(*args, **kwargs):
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

        query = kwargs.get('params', {}).get('q', '').lower()
        limit = kwargs.get('params', {}).get('limit', 3)

        if "smartphone" in query:
            logger.info("Mocking products for 'smartphone'.")
            return MockResponse(200, {
                "products": [
                    {"id": "prod-101", "name": "Smartphone X", "price": 1200.00, "currency": "BRL", "store": "LojaTech", "url": "https://loja.tech/smartphone-x"},
                    {"id": "prod-102", "name": "Smartphone Y Pro", "price": 1800.00, "currency": "BRL", "store": "MegaEletronicos", "url": "https://megaeletronicos.com/smartphone-y"},
                ][:limit]
            })
        elif "livro" in query:
            logger.info("Mocking products for 'livro'.")
            return MockResponse(200, {
                "products": [
                    {"id": "book-201", "name": "Dom Quixote", "price": 50.00, "currency": "BRL", "store": "LivrariaDigital", "url": "https://livrariadigital.com/dom-quixote"},
                ][:limit]
            })
        elif "sem resultados" in query:
            logger.info("Mocking no results for 'sem resultados'.")
            return MockResponse(200, {"products": []})
        elif "erro api" in query:
            logger.info("Mocking API error for 'erro api'.")
            return MockResponse(400, {"error": "Invalid query"})
        else:
            logger.warning(f"No specific mock for query: '{query}'. Returning empty.")
            return MockResponse(200, {"products": []})

    # Patch httpx.AsyncClient.get with our mock for testing
    original_httpx_get_ecommerce = httpx.AsyncClient.get
    httpx.AsyncClient.get = mock_httpx_get_ecommerce

    async def run_ecommerce_manager_tests():
        print("\n--- Iniciando Testes do EcommerceManager ---")

        dummy_gem = DummyGEM(logger)
        ecommerce_manager = EcommerceManager(dummy_gem, logger)
        
        ecommerce_manager.register_commands(dummy_gem.command_executor)

        await ecommerce_manager.initialize()

        # --- Teste 1: Pesquisar Produtos ---
        print("\n--- Teste 1: Pesquisar Produtos ---")
        result_search_smartphone = await dummy_gem.command_executor.execute(
            "search_products", query="smartphone", limit=1
        )
        print(result_search_smartphone["output"])
        assert result_search_smartphone["success"] is True
        assert "Smartphone X" in result_search_smartphone["output"]
        assert "Resultados da pesquisa para 'smartphone':" in result_search_smartphone["output"]

        result_search_book = await dummy_gem.command_executor.execute(
            "search_products", query="livro"
        )
        print(result_search_book["output"])
        assert result_search_book["success"] is True
        assert "Dom Quixote" in result_search_book["output"]

        # --- Teste 2: Adicionar à Lista de Desejos ---
        print("\n--- Teste 2: Adicionar à Lista de Desejos ---")
        result_add_wishlist = await dummy_gem.command_executor.execute(
            "add_to_wishlist",
            product_name="Fone de Ouvido Sem Fio",
            price=250.00,
            currency="BRL",
            store="Eletronicos.com",
            url="https://eletronicos.com/fone",
            description="Fone de alta qualidade com cancelamento de ruído."
        )
        print(result_add_wishlist["output"])
        assert result_add_wishlist["success"] is True
        assert "'Fone de Ouvido Sem Fio' adicionado à sua lista de desejos." in result_add_wishlist["output"]
        
        result_add_wishlist2 = await dummy_gem.command_executor.execute(
            "add_to_wishlist",
            product_name="Smartwatch Avançado",
            price=700.00,
            currency="BRL",
            store="WatchStore",
        )
        assert result_add_wishlist2["success"] is True


        # --- Teste 3: Listar Lista de Desejos ---
        print("\n--- Teste 3: Listar Lista de Desejos ---")
        result_list_wishlist = await dummy_gem.command_executor.execute("list_wishlist")
        print(result_list_wishlist["output"])
        assert result_list_wishlist["success"] is True
        assert "Fone de Ouvido Sem Fio" in result_list_wishlist["output"]
        assert "Smartwatch Avançado" in result_list_wishlist["output"]
        assert "Sua lista de desejos:" in result_list_wishlist["output"]

        # --- Teste 4: Remover da Lista de Desejos ---
        print("\n--- Teste 4: Remover da Lista de Desejos ---")
        product_id_to_remove = next(p.id for p in ecommerce_manager._wishlist.values() if p.name == "Fone de Ouvido Sem Fio")
        result_remove_wishlist = await dummy_gem.command_executor.execute(
            "remove_from_wishlist", product_id_prefix=product_id_to_remove[:8]
        )
        print(result_remove_wishlist["output"])
        assert result_remove_wishlist["success"] is True
        assert "'Fone de Ouvido Sem Fio' (ID:" in result_remove_wishlist["output"] and "removido da sua lista de desejos." in result_remove_wishlist["output"]
        
        # Verify removal
        assert product_id_to_remove not in ecommerce_manager._wishlist

        # --- Teste 5: Pesquisar Produtos Sem Resultados ---
        print("\n--- Teste 5: Pesquisar Produtos Sem Resultados ---")
        result_no_products = await dummy_gem.command_executor.execute(
            "search_products", query="consulta sem resultados"
        )
        print(result_no_products["output"])
        assert result_no_products["success"] is True
        assert "Não foram encontrados produtos para a pesquisa: 'consulta sem resultados'." in result_no_products["output"]

        # --- Teste 6: Simular Erro de API na Pesquisa ---
        print("\n--- Teste 6: Simular Erro de API na Pesquisa ---")
        result_api_error = await dummy_gem.command_executor.execute(
            "search_products", query="erro api"
        )
        print(result_api_error["output"])
        assert result_api_error["success"] is False
        assert "Desculpe, houve um erro ao buscar produtos." in dummy_gem.notification_manager._history[-1]["message"]


        print("\n--- Testes do EcommerceManager concluídos com sucesso. ---")
        await ecommerce_manager.shutdown()
        
        # Restore original httpx.AsyncClient.get
        httpx.AsyncClient.get = original_httpx_get_ecommerce

    asyncio.run(run_ecommerce_manager_tests())

