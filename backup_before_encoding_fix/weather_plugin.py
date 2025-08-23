#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📚🌦️ GEM OS - Wikipedia & Weather Plugin (plugins/combined_plugin.py)

Provides quick summaries from Wikipedia and a complete weather service for a given city or location.
Registers commands with PluginManager:
- "wiki:search"
- "weather:get"
- "weather:forecast"
- "weather:hourly"
"""

from __future__ import annotations
import wikipedia
import requests
import json
import os
from typing import Dict, Any

# Configure Wikipedia language
wikipedia.set_lang("pt")

# Configure Weather API
CONFIG_FILE = "data/weather_config.json"
API_URL = "https://api.openweathermap.org/data/2.5"
API_KEY = os.getenv("OPENWEATHER_API_KEY", None)


def _load_config() -> Dict[str, Any]:
    """Load OpenWeather API key from config file or environment variable."""
    if API_KEY:
        return {"api_key": API_KEY}
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _get_current_location() -> str:
    """
    Placeholder function to get the user's current city.
    In a real-world application, this would use a geolocation
    service (e.g., based on IP address) to determine the city.
    """
    return "São Paulo"


def wiki_search(query: str, sentences: int = 2) -> str:
    """Fetch a short Wikipedia summary for a query."""
    try:
        summary = wikipedia.summary(query, sentences=sentences)
        return f"📚 {query}: {summary}"
    except wikipedia.exceptions.DisambiguationError as e:
        return f"❌ The query '{query}' is ambiguous. Options: {', '.join(e.options[:5])}"
    except wikipedia.exceptions.PageError:
        return f"❌ No results found for '{query}'."
    except Exception as e:
        return f"⚠️ Error fetching Wikipedia data: {e}"


def get_weather(city: str = None, lang: str = "pt", units: str = "metric") -> str:
    """Get current weather for a city."""
    if city is None:
        city = _get_current_location()
        
    cfg = _load_config()
    if not cfg.get("api_key"):
        return "⚠️ Weather config missing (data/weather_config.json or OPENWEATHER_API_KEY)."

    try:
        params = {"q": city, "appid": cfg["api_key"], "lang": lang, "units": units}
        r = requests.get(f"{API_URL}/weather", params=params, timeout=10)
        r.raise_for_status()
        data = r.json()

        desc = data["weather"][0]["description"].capitalize()
        temp = data["main"]["temp"]
        feels = data["main"]["feels_like"]
        humidity = data["main"]["humidity"]

        return f"🌡️ Clima em {city}: {desc}, {temp}°C (sensação {feels}°C), 💧 {humidity}%"
    except Exception as e:
        return f"❌ Error fetching weather: {e}"


def get_forecast(city: str = None, days: int = 3, lang: str = "pt", units: str = "metric") -> str:
    """Get daily forecast for the next N days."""
    if city is None:
        city = _get_current_location()

    cfg = _load_config()
    if not cfg.get("api_key"):
        return "⚠️ Weather config missing."

    try:
        params = {"q": city, "appid": cfg["api_key"], "cnt": days, "lang": lang, "units": units}
        r = requests.get(f"{API_URL}/forecast/daily", params=params, timeout=10)
        if r.status_code == 404:
            return "⚠️ Daily forecast not available on free plan."
        r.raise_for_status()
        data = r.json()

        lines = []
        for d in data.get("list", []):
            desc = d["weather"][0]["description"]
            temp_min = d["temp"]["min"]
            temp_max = d["temp"]["max"]
            lines.append(f"📅 {desc} → {temp_min}°C ~ {temp_max}°C")

        return f"📊 Previsão para {city}:\n" + "\n".join(lines)
    except Exception as e:
        return f"❌ Error fetching forecast: {e}"


def get_hourly(city: str = None, hours: int = 6, lang: str = "pt", units: str = "metric") -> str:
    """Get 3-hour forecast for the next N hours."""
    if city is None:
        city = _get_current_location()

    cfg = _load_config()
    if not cfg.get("api_key"):
        return "⚠️ Weather config missing."

    try:
        params = {"q": city, "appid": cfg["api_key"], "lang": lang, "units": units}
        r = requests.get(f"{API_URL}/forecast", params=params, timeout=10)
        r.raise_for_status()
        data = r.json()

        lines = []
        for f in data.get("list", [])[:hours // 3]:
            desc = f["weather"][0]["description"]
            temp = f["main"]["temp"]
            dt_txt = f["dt_txt"]
            lines.append(f"⏰ {dt_txt}: {desc}, {temp}°C")

        return f"🕒 Previsão horária em {city}:\n" + "\n".join(lines)
    except Exception as e:
        return f"❌ Error fetching hourly forecast: {e}"


def register(plugin_manager):
    """Register all plugin commands."""
    plugin_manager.register_command("wiki:search", wiki_search)
    plugin_manager.register_command("weather:get", get_weather)
    plugin_manager.register_command("weather:forecast", get_forecast)
    plugin_manager.register_command("weather:hourly", get_hourly)
