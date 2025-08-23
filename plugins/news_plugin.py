#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ğŸ“° GEM OS - Plugin de NotÃ­cias (plugins/news_plugin.py)

Fornece as Ãºltimas manchetes de notÃ­cias usando a NewsAPI.
Registra o comando "news:get" com o PluginManager.

Para usar este plugin, vocÃª precisarÃ¡ de uma chave de API da NewsAPI.
1. Visite https://newsapi.org/ e registre-se para obter uma chave de desenvolvedor gratuita.
2. Configure sua chave de API de uma das seguintes maneiras:
   a) **Recomendado (VariÃ¡vel de Ambiente):** Defina uma variÃ¡vel de ambiente chamada `NEWS_API_KEY`
      com sua chave de API. Por exemplo (Linux/macOS):
      export NEWS_API_KEY="SUA_CHAVE_AQUI"
      Ou (Windows PowerShell):
      $env:NEWS_API_KEY="SUA_CHAVE_AQUI"
   b) **Arquivo de ConfiguraÃ§Ã£o (news_config.json):** Crie um arquivo `data/news_config.json`
      no mesmo diretÃ³rio da sua aplicaÃ§Ã£o (ou um que seja acessÃ­vel) com o seguinte conteÃºdo:
      {
          "api_key": "SUA_CHAVE_AQUI"
      }
"""

from __future__ import annotations
import requests
import json
import os
from typing import Dict, Any, List

# Caminhos de configuraÃ§Ã£o e URL da API
CONFIG_FILE = "data/news_config.json"
BASE_API_URL = "https://newsapi.org/v2/top-headlines"

def _load_api_key() -> str | None:
    """
    Tenta carregar a chave da API de NEWS_API_KEY ou de um arquivo de configuraÃ§Ã£o.
    Retorna a chave da API se encontrada, caso contrÃ¡rio, retorna None.
    """
    # Tenta carregar da variÃ¡vel de ambiente primeiro (prioridade)
    api_key = os.getenv("NEWS_API_KEY")
    if api_key:
        return api_key

    # Se nÃ£o estiver na variÃ¡vel de ambiente, tenta do arquivo de configuraÃ§Ã£o
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
                return config.get("api_key")
        except json.JSONDecodeError:
            print(f"âš ï¸� Erro ao decodificar JSON em {CONFIG_FILE}. Verifique a sintaxe do arquivo.")
        except Exception as e:
            print(f"âš ï¸� Erro ao carregar o arquivo de configuraÃ§Ã£o {CONFIG_FILE}: {e}")
    return None

def get_news(country: str = "us", category: str = "general", limit: int = 5) -> str:
    """
    Busca as Ãºltimas manchetes de notÃ­cias para um determinado paÃ­s e categoria.

    Args:
        country (str): O cÃ³digo do paÃ­s (ex: "us", "br"). PadrÃ£o Ã© "us".
        category (str): A categoria das notÃ­cias (ex: "technology", "sports", "general"). PadrÃ£o Ã© "general".
        limit (int): O nÃºmero mÃ¡ximo de artigos a serem retornados. PadrÃ£o Ã© 5.

    Returns:
        str: Uma string formatada com as manchetes das notÃ­cias ou uma mensagem de erro.
    """
    api_key = _load_api_key()

    if not api_key:
        # Fallback offline se a chave da API nÃ£o estiver configurada
        return (
            f"ğŸ“° NotÃ­cias Offline: {category.title()} â€” Falha na configuraÃ§Ã£o da API NewsAPI. "
            "Verifique se NEWS_API_KEY estÃ¡ definida ou se 'data/news_config.json' existe com sua chave."
        )

    try:
        params = {
            "country": country,
            "category": category,
            "pageSize": limit,
            "apiKey": api_key,
            "language": "pt" # Define a linguagem das notÃ­cias para portuguÃªs
        }
        
        # Realiza a requisiÃ§Ã£o HTTP para a NewsAPI
        response = requests.get(BASE_API_URL, params=params, timeout=10)
        response.raise_for_status()  # LanÃ§a uma exceÃ§Ã£o para cÃ³digos de status HTTP de erro (4xx ou 5xx)
        data = response.json()

        if not data.get("articles"):
            return f"ğŸ“­ Nenhuma notÃ­cia encontrada para '{category}' em '{country}'. Tente uma categoria ou paÃ­s diferente."

        lines: List[str] = []
        for article in data["articles"]:
            title = article.get("title", "TÃ­tulo Desconhecido")
            source = article.get("source", {}).get("name", "Fonte Desconhecida")
            url = article.get("url", "#")
            lines.append(f"ğŸ“° {title} (Fonte: {source}) -> {url}")

        return f"ğŸ“¢ Ãšltimas NotÃ­cias ({country.upper()}/{category.title()}): \n" + "\n".join(lines)

    except requests.exceptions.HTTPError as http_err:
        status_code = http_err.response.status_code
        if status_code == 401:
            return "â�Œ Erro de autenticaÃ§Ã£o da NewsAPI. Sua chave de API pode ser invÃ¡lida ou expirada."
        elif status_code == 429:
            return "â�Œ Limite de requisiÃ§Ãµes da NewsAPI excedido. Tente novamente mais tarde."
        else:
            return f"â�Œ Erro HTTP ao buscar notÃ­cias: {http_err} (CÃ³digo: {status_code})"
    except requests.exceptions.ConnectionError as conn_err:
        return f"â�Œ Erro de conexÃ£o ao buscar notÃ­cias. Verifique sua internet: {conn_err}"
    except requests.exceptions.Timeout as timeout_err:
        return f"â�Œ A requisiÃ§Ã£o de notÃ­cias expirou: {timeout_err}. Tente novamente."
    except requests.exceptions.RaquestException as req_err:
        return f"â�Œ Um erro inesperado ocorreu durante a requisiÃ§Ã£o: {req_err}"
    except Exception as e:
        return f"â�Œ Um erro desconhecido ocorreu: {e}"


def register(plugin_manager):
    """
    Registra o comando "news:get" com o PluginManager.
    """
    plugin_manager.register_command("news:get", get_news)

