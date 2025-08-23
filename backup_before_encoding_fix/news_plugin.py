#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📰 GEM OS - Plugin de Notícias (plugins/news_plugin.py)

Fornece as últimas manchetes de notícias usando a NewsAPI.
Registra o comando "news:get" com o PluginManager.

Para usar este plugin, você precisará de uma chave de API da NewsAPI.
1. Visite https://newsapi.org/ e registre-se para obter uma chave de desenvolvedor gratuita.
2. Configure sua chave de API de uma das seguintes maneiras:
   a) **Recomendado (Variável de Ambiente):** Defina uma variável de ambiente chamada `NEWS_API_KEY`
      com sua chave de API. Por exemplo (Linux/macOS):
      export NEWS_API_KEY="SUA_CHAVE_AQUI"
      Ou (Windows PowerShell):
      $env:NEWS_API_KEY="SUA_CHAVE_AQUI"
   b) **Arquivo de Configuração (news_config.json):** Crie um arquivo `data/news_config.json`
      no mesmo diretório da sua aplicação (ou um que seja acessível) com o seguinte conteúdo:
      {
          "api_key": "SUA_CHAVE_AQUI"
      }
"""

from __future__ import annotations
import requests
import json
import os
from typing import Dict, Any, List

# Caminhos de configuração e URL da API
CONFIG_FILE = "data/news_config.json"
BASE_API_URL = "https://newsapi.org/v2/top-headlines"

def _load_api_key() -> str | None:
    """
    Tenta carregar a chave da API de NEWS_API_KEY ou de um arquivo de configuração.
    Retorna a chave da API se encontrada, caso contrário, retorna None.
    """
    # Tenta carregar da variável de ambiente primeiro (prioridade)
    api_key = os.getenv("NEWS_API_KEY")
    if api_key:
        return api_key

    # Se não estiver na variável de ambiente, tenta do arquivo de configuração
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
                return config.get("api_key")
        except json.JSONDecodeError:
            print(f"⚠️ Erro ao decodificar JSON em {CONFIG_FILE}. Verifique a sintaxe do arquivo.")
        except Exception as e:
            print(f"⚠️ Erro ao carregar o arquivo de configuração {CONFIG_FILE}: {e}")
    return None

def get_news(country: str = "us", category: str = "general", limit: int = 5) -> str:
    """
    Busca as últimas manchetes de notícias para um determinado país e categoria.

    Args:
        country (str): O código do país (ex: "us", "br"). Padrão é "us".
        category (str): A categoria das notícias (ex: "technology", "sports", "general"). Padrão é "general".
        limit (int): O número máximo de artigos a serem retornados. Padrão é 5.

    Returns:
        str: Uma string formatada com as manchetes das notícias ou uma mensagem de erro.
    """
    api_key = _load_api_key()

    if not api_key:
        # Fallback offline se a chave da API não estiver configurada
        return (
            f"📰 Notícias Offline: {category.title()} — Falha na configuração da API NewsAPI. "
            "Verifique se NEWS_API_KEY está definida ou se 'data/news_config.json' existe com sua chave."
        )

    try:
        params = {
            "country": country,
            "category": category,
            "pageSize": limit,
            "apiKey": api_key,
            "language": "pt" # Define a linguagem das notícias para português
        }
        
        # Realiza a requisição HTTP para a NewsAPI
        response = requests.get(BASE_API_URL, params=params, timeout=10)
        response.raise_for_status()  # Lança uma exceção para códigos de status HTTP de erro (4xx ou 5xx)
        data = response.json()

        if not data.get("articles"):
            return f"📭 Nenhuma notícia encontrada para '{category}' em '{country}'. Tente uma categoria ou país diferente."

        lines: List[str] = []
        for article in data["articles"]:
            title = article.get("title", "Título Desconhecido")
            source = article.get("source", {}).get("name", "Fonte Desconhecida")
            url = article.get("url", "#")
            lines.append(f"📰 {title} (Fonte: {source}) -> {url}")

        return f"📢 Últimas Notícias ({country.upper()}/{category.title()}): \n" + "\n".join(lines)

    except requests.exceptions.HTTPError as http_err:
        status_code = http_err.response.status_code
        if status_code == 401:
            return "❌ Erro de autenticação da NewsAPI. Sua chave de API pode ser inválida ou expirada."
        elif status_code == 429:
            return "❌ Limite de requisições da NewsAPI excedido. Tente novamente mais tarde."
        else:
            return f"❌ Erro HTTP ao buscar notícias: {http_err} (Código: {status_code})"
    except requests.exceptions.ConnectionError as conn_err:
        return f"❌ Erro de conexão ao buscar notícias. Verifique sua internet: {conn_err}"
    except requests.exceptions.Timeout as timeout_err:
        return f"❌ A requisição de notícias expirou: {timeout_err}. Tente novamente."
    except requests.exceptions.RaquestException as req_err:
        return f"❌ Um erro inesperado ocorreu durante a requisição: {req_err}"
    except Exception as e:
        return f"❌ Um erro desconhecido ocorreu: {e}"


def register(plugin_manager):
    """
    Registra o comando "news:get" com o PluginManager.
    """
    plugin_manager.register_command("news:get", get_news)

