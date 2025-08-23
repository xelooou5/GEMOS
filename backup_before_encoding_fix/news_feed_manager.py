#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
?? GEM OS - News Feed Manager (core/news_feed_manager.py)
Fetches and manages personalized news feeds.

Responsibilities
----------------
- Integrates with news APIs and RSS feeds.
- Filters and formats articles based on user preferences.
- Provides caching and error handling for robustness.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

import aiohttp
import feedparser

from core.gem_config_manager import GEMConfigManager


class NewsFeedManager:
    """
    Fetches and manages news feeds based on user preferences.
    """

    def __init__(self, config_manager: GEMConfigManager, logger: Optional[logging.Logger] = None):
        self.config_manager = config_manager
        self.logger = logger or logging.getLogger(__name__)

        # Preferências de usuário
        self.sources: List[str] = self.config_manager.get("news.sources", [])
        self.keywords: List[str] = self.config_manager.get("news.keywords", [])
        self.language: str = self.config_manager.get("news.language", "pt")

        # Cache simples de artigos
        self.cache: Dict[str, Any] = {}

        self.logger.info("NewsFeedManager inicializado.")

    # ------------------------------------------------------------------ API News

    async def fetch_api_news(self, session: aiohttp.ClientSession, url: str) -> List[Dict[str, Any]]:
        """Busca notícias de uma API JSON."""
        try:
            async with session.get(url, timeout=20) as resp:
                if resp.status != 200:
                    self.logger.warning(f"API {url} retornou status {resp.status}")
                    return []
                data = await resp.json()
                return data.get("articles", [])
        except Exception as e:
            self.logger.error(f"Erro ao buscar API {url}: {e}", exc_info=True)
            return []

    # ------------------------------------------------------------------ RSS Feeds

    async def fetch_rss_feed(self, session: aiohttp.ClientSession, url: str) -> List[Dict[str, Any]]:
        """Busca notícias de um feed RSS."""
        try:
            async with session.get(url, timeout=20) as resp:
                if resp.status != 200:
                    self.logger.warning(f"RSS {url} retornou status {resp.status}")
                    return []
                text = await resp.text()
                parsed = feedparser.parse(text)
                return [
                    {
                        "title": entry.get("title", ""),
                        "link": entry.get("link", ""),
                        "summary": entry.get("summary", ""),
                        "published": entry.get("published", ""),
                    }
                    for entry in parsed.entries
                ]
        except Exception as e:
            self.logger.error(f"Erro ao buscar RSS {url}: {e}", exc_info=True)
            return []

    # ------------------------------------------------------------------ Agregador

    async def fetch_all_news(self) -> List[Dict[str, Any]]:
        """Busca notícias de todas as fontes configuradas."""
        self.logger.info("Buscando notícias de todas as fontes...")

        articles: List[Dict[str, Any]] = []
        async with aiohttp.ClientSession() as session:
            tasks = []
            for url in self.sources:
                if url.endswith(".xml") or "rss" in url:
                    tasks.append(self.fetch_rss_feed(session, url))
                else:
                    tasks.append(self.fetch_api_news(session, url))

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for res in results:
                if isinstance(res, Exception):
                    self.logger.error(f"Erro em uma das fontes: {res}")
                    continue
                articles.extend(res)

        filtered = self.filter_articles(articles)
        self.logger.info(f"? {len(filtered)} artigos obtidos após filtros.")
        return filtered

    # ------------------------------------------------------------------ Filtros

    def filter_articles(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filtra artigos por idioma e palavras-chave."""
        if not articles:
            return []

        results = []
        for art in articles:
            title = art.get("title", "").lower()
            summary = art.get("summary", "").lower()

            if self.keywords and not any(kw.lower() in (title + summary) for kw in self.keywords):
                continue

            results.append(art)

        return results

    # ------------------------------------------------------------------ Cache

    def cache_articles(self, articles: List[Dict[str, Any]]) -> None:
        """Armazena artigos em cache simples (memória)."""
        for art in articles:
            key = art.get("link") or art.get("title")
            if key:
                self.cache[key] = art
        self.logger.debug(f"{len(articles)} artigos adicionados ao cache.")

    def get_cached_articles(self) -> List[Dict[str, Any]]:
        """Retorna todos os artigos em cache."""
        return list(self.cache.values())
