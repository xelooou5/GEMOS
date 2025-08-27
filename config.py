#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
💎 GEM OS - TalkAI Configuration
This file centralizes settings for the voice assistant.
English first, Portuguese (pt-BR) second.
"""

# --- Wake Word Configuration ---
# The word that activates the assistant. / A palavra que ativa o assistente.
WAKE_WORD = 'gemini'  # Options from pvporcupine: 'gemini', 'porcupine', 'bumblebee', 'alexa', etc.

# --- Voice Configuration ---
# Amazon Polly voice ID. / ID da voz do Amazon Polly.
POLLY_VOICE = 'Joanna'  # Example voices: 'Joanna' (US), 'Vitoria' (BR), 'Brian' (UK)

# --- Language Configuration ---
# Language code for speech-to-text. / Código de idioma para reconhecimento de voz.
LANGUAGE_CODE = 'en-US'  # Examples: 'en-US', 'pt-BR', 'en-GB'

# --- Command Configuration ---
# Phrases that will reset the conversation history. / Frases que irão reiniciar o histórico da conversa.
RESET_COMMANDS = ['reset conversation', 'clear history', 'forget everything', 'start over']

# --- Accessibility Configuration ---
# Phrases that will toggle emergency accessibility mode. / Frases que irão ativar o modo de acessibilidade de emergência.
ACCESSIBILITY_MODE_COMMANDS = ['emergency mode', 'accessibility on', 'screen reader mode', 'accessibility mode']