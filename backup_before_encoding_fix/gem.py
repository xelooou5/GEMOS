#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
💎 GEM OS - Generative Enhanced Microphone
Assistente de Voz Local para Acessibilidade Universal

🎯 Mission: Creating an accessible, offline-first AI voice assistant
for children, people with disabilities, elderly users, and everyone
who needs technology that truly understands and serves humanity.

🌟 Features:
- 🔒 100% Offline: Complete privacy, no data leaves your computer
- ♿ Accessibility: Designed for people with different needs
- 🧠 Local AI: Powered by Ollama + Phi3 for intelligent responses
- 🎤 Voice Recognition: Whisper for precise transcription
- 🗣️ Voice Synthesis: Multiple engines (espeak, spd-say, festival)
- 👂 Wake Word: "Hey GEM" activation detection
- ⚙️ Configurable: Complete TUI interface for customization
- 🌍 Multilingual: Multiple language support
- 🔌 Extensible: Plugin system for additional functionality

Author: GEM Project
Date: 2025-08-22
Version: 2.0.0 - Unified Enhanced Edition
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import platform
import signal
import sys
import threading
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional, Any, Dict, List, Coroutine, Awaitable
import inspect

# Add project root to Python path for easier imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# =========================
# Core / Features imports with graceful fallbacks
# =========================
def safe_import(module_path: str):
    """Safely import a module from a path, returning it or None."""
    try:
        if "." in module_path:
            module = __import__(module_path)
            # Traverse nested modules
            for part in module_path.split(".")[1:]:
                module = getattr(module, part)
            return module
        else:
            return __import__(module_path)
    except ImportError as e:
        print(f"⚠️ Warning: Cannot import module '{module_path}'. Reason: {e}")
        return None
    except Exception as e:
        print(f"❌ Error during module import '{module_path}'. Reason: {e}")
        return None

# Import core components using the new, safer method
audio_system_module = safe_import("core.audio_system")
config_manager_module = safe_import("core.config_manager")
stt_module = safe_import("core.stt_module")
tts_module = safe_import("core.tts_module")
llm_handler_module = safe_import("core.llm_handler")
command_executor_module = safe_import("core.command_executor")
storage_module = safe_import("core.storage")
plugins_module = safe_import("core.plugins")

# Map imported modules to their classes
AudioSystem = getattr(audio_system_module, "AudioSystem", None)
GEMConfigManager = getattr(config_manager_module, "GEMConfigManager", None)
STTModule = getattr(stt_module, "STTModule", None)
TTSModule = getattr(tts_module, "TTSModule", None)
LLMHandler = getattr(llm_handler_module, "LLMHandler", None)
CommandExecutor = getattr(command_executor_module, "CommandExecutor", None)
Storage = getattr(storage_module, "Storage", None)
PluginManager = getattr(plugins_module, "PluginManager", None)

class SystemState:
    """Class to manage the state of the GEM OS."""
    def __init__(self):
        self.is_running: bool = False
        self.is_processing_request: bool = False
        self.is_listening: bool = False
        self.is_awake: bool = False
        self.stop_requested: bool = False

class GEMVoiceAssistant:
    def __init__(self, config_file: str = "config.json", profile: str = "default", debug: bool = False):
        self.state = SystemState()
        self.config_manager: Optional[GEMConfigManager] = None
        self.audio_system: Optional[AudioSystem] = None
        self.stt_module: Optional[STTModule] = None
        self.tts_module: Optional[TTSModule] = None
        self.llm_handler: Optional[LLMHandler] = None
        self.command_executor: Optional[CommandExecutor] = None
        self.storage: Optional[Storage] = None
        self.plugin_manager: Optional[PluginManager] = None
        
        self.conversation_context: List[Dict[str, Any]] = []
        self.logger = self._setup_logging(debug)
        self.logger.info("Initializing GEM OS...")

        # Initialize Config Manager first, it's the foundation
        if not GEMConfigManager:
            self.logger.error("❌ GEMConfigManager class not found. Cannot proceed.")
            sys.exit(1)
        
        self.config_manager = GEMConfigManager(config_file=config_file)
        self.config_manager.load(profile=profile)
        self._update_system_from_config()

    def _setup_logging(self, debug: bool):
        """Initializes logging with a custom format."""
        log_level = logging.DEBUG if debug else logging.INFO
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        return logging.getLogger("GEMVoiceAssistant")

    def _update_system_from_config(self):
        """Applies configuration settings to the system."""
        self.logger.info("Applying system configuration...")
        config = self.config_manager.get_config()
        self.conversation_context = config.get("initial_context", [])

    async def initialize_systems(self):
        """Initializes all core modules with error handling."""
        self.logger.info("Starting system initialization...")
        config = self.config_manager.get_config()

        # Initialize Audio System
        try:
            self.audio_system = AudioSystem(config=config.get("audio", {}), logger=self.logger)
            await self.audio_system.initialize()
            self.logger.info("✅ Audio System initialized.")
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize Audio System: {e}")
            self.audio_system = None
            
        # Initialize STT Module
        try:
            self.stt_module = STTModule(config=config.get("stt", {}), logger=self.logger)
            await self.stt_module.initialize()
            self.logger.info("✅ STT Module initialized.")
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize STT Module: {e}")
            self.stt_module = None

        # Initialize TTS Module
        try:
            self.tts_module = TTSModule(config=config.get("tts", {}), logger=self.logger)
            await self.tts_module.initialize()
            self.logger.info("✅ TTS Module initialized.")
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize TTS Module: {e}")
            self.tts_module = None

        # Initialize LLM Handler
        try:
            self.llm_handler = LLMHandler(config=config.get("llm", {}), logger=self.logger)
            self.logger.info("✅ LLM Handler initialized.")
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize LLM Handler: {e}")
            self.llm_handler = None

        # Initialize Storage and Plugin Manager
        try:
            self.storage = Storage(config=config.get("storage", {}), logger=self.logger)
            self.plugin_manager = PluginManager(self, logger=self.logger)
            self.command_executor = CommandExecutor(
                self.llm_handler, self.plugin_manager, self.storage, self.logger
            )
            self.logger.info("✅ Core modules (Storage, Plugins, Commands) initialized.")
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize core modules: {e}")
            self.storage = self.plugin_manager = self.command_executor = None

        self.logger.info("System initialization complete.")
        
        # Announce readiness
        if self.tts_module:
            await self.tts_module.speak("Olá. Eu sou o GEM. Como posso ajudar?")

    async def _process_user_query(self, query: str):
        """Processes a user's transcribed query."""
        if not self.state.is_awake:
            if "hey gem" in query.lower():
                self.logger.info("💎 Wake word detected.")
                self.state.is_awake = True
                await self._safe_tts_speak("Olá, pode falar.")
                return

        if self.state.is_awake:
            self.logger.info(f"🎤 Comando recebido: '{query}'")
            self.state.is_processing_request = True
            
            response = "Desculpe, não entendi o que você disse."
            
            if self.command_executor:
                is_handled, executor_response = await self.command_executor.execute_command(query)
                if is_handled:
                    response = executor_response
                elif self.llm_handler:
                    self.conversation_context.append({"role": "user", "content": query})
                    try:
                        llm_response_gen = self.llm_handler.stream_response(self.conversation_context)
                        # Process response as it streams
                        response = ""
                        async for chunk in llm_response_gen:
                            response += chunk
                        self.conversation_context.append({"role": "assistant", "content": response})
                    except Exception as e:
                        self.logger.error(f"❌ LLM request failed: {e}")
                        response = "Desculpe, não consegui me conectar com a inteligência artificial."
            
            await self._safe_tts_speak(response)
            self.state.is_processing_request = False
            self.state.is_awake = False
            
    async def _safe_tts_speak(self, text: str) -> None:
        """Safely speaks text, handling potential TTS failures."""
        if self.tts_module:
            await self.tts_module.speak(text)
        else:
            self.logger.warning("TTS module not available. Cannot speak.")
    
    async def run(self, dry_run: bool = False):
        """Main event loop for the assistant."""
        if not self.audio_system or not self.stt_module:
            self.logger.error("❌ Audio or STT systems not available. Aborting run.")
            return

        self.state.is_running = True
        self.logger.info("🚀 GEM OS is now running. Awaiting wake word...")

        while self.state.is_running and not self.state.stop_requested:
            try:
                self.state.is_listening = True
                self.logger.debug("Listening for audio...")
                
                audio_data = await self.audio_system.capture_audio()
                if audio_data:
                    self.logger.debug("Audio captured. Processing...")
                    transcribed_text = await self.stt_module.transcribe(audio_data)
                    if transcribed_text:
                        self.logger.debug(f"Transcribed: '{transcribed_text}'")
                        await self._process_user_query(transcribed_text)
                    else:
                        self.logger.info("No speech detected or transcription failed.")
                        
            except asyncio.CancelledError:
                self.logger.info("Main loop was cancelled.")
                break
            except Exception as e:
                self.logger.error(f"❌ An unexpected error occurred in the main loop: {e}")
                self.state.is_running = False
                await self._safe_tts_speak("Um erro crítico ocorreu. Estou sendo desligado.")
        
        self.shutdown()

    def shutdown(self):
        """Gracefully shuts down the system."""
        self.logger.info("⚠️ Shutting down GEM OS...")
        self.state.is_running = False
        self.state.stop_requested = True
        if self.audio_system:
            self.audio_system.shutdown()
        if self.tts_module:
            asyncio.run(self.tts_module.speak("Desligando."))
            self.tts_module.shutdown()
        self.logger.info("✅ Shutdown complete.")
        sys.exit(0)

def parse_args():
    """Parses command-line arguments."""
    parser = argparse.ArgumentParser(description="💎 GEM OS - A Local Voice Assistant.")
    parser.add_argument("--config", type=str, default="data/config.json", help="Path to the configuration file.")
    parser.add_argument("--profile", type=str, default="default", help="The configuration profile to use.")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging.")
    parser.add_argument("--voice-test", action="store_true", help="Run a quick voice synthesis test.")
    parser.add_argument("--audio-test", action="store_true", help="Run a quick audio capture test.")
    parser.add_argument("--dry-run", action="store_true", help="Run the system without processing voice commands.")
    return parser.parse_args()

def setup_signal_handlers(gem: GEMVoiceAssistant):
    """Sets up signal handlers for graceful shutdown."""
    def signal_handler(signum, frame):
        gem.logger.info(f"Signal {signum} received. Initiating graceful shutdown.")
        gem.state.stop_requested = True
    
    if platform.system() != 'Windows':
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

async def main_async():
    """Main async entry point"""
    args = parse_args()
    
    # Initialize the main assistant object
    gem = GEMVoiceAssistant(config_file=args.config, profile=args.profile, debug=args.debug)
    setup_signal_handlers(gem)
    
    if args.voice_test:
        if gem.tts_module:
            await gem.tts_module.speak("Olá, o teste de voz do GEM foi bem-sucedido.")
        return

    if args.audio_test:
        if gem.audio_system:
            await gem.audio_system.test_audio_capture()
        return

    if args.dry_run:
        gem.logger.info("Running in dry-run mode. Initialization only.")
        await gem.initialize_systems()
        return

    await gem.initialize_systems()
    await gem.run()
    gem.shutdown()

def main():
    """Wrapper for main_async to handle different Python versions."""
    if sys.version_info >= (3, 7):
        asyncio.run(main_async())
    else:
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(main_async())
        finally:
            loop.close()

if __name__ == "__main__":
    main()
