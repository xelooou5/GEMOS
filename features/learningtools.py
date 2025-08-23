#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
üíé GEM OS - Main Application Entry Point
Consolidated version with Claude-style clarity + Gemini-style UX robustness.

Author: GEM Project
Date: 2025-08-22
"""

import argparse
import asyncio
import signal
import sys
import time
from pathlib import Path

from core.audio_system import AudioSystem
from core.command_executor import CommandExecutor
from core.config_manager import ConfigManager
from core.llm_handler import LLMHandler
from core.stt_module import STTModule
from core.tts_module import TTSModule

# =============================================================================
# GEM CORE CLASS
# =============================================================================

class GEM:
    """
    Main GEM OS orchestrator.
    Handles initialization, event loop, and subsystem coordination.
    """

    def __init__(self, config_path: str = "data/config.json", profile: str = "default", debug: bool = False):
        self.start_time = time.time()
        self.config_manager = ConfigManager(config_path=config_path)
        self.profile = profile
        self.debug = debug

        # Subsystems
        self.audio = None
        self.stt = None
        self.tts = None
        self.llm = None
        self.executor = None

        # State
        self.running = False
        self.interaction_count = 0
        self.failed_modules = []

    # -------------------------------------------------------------------------
    # INITIALIZATION
    # -------------------------------------------------------------------------

    def initialize(self):
        """Initialize all GEM subsystems with graceful fallback."""
        print("üíé Initializing GEM OS...")

        try:
            self.audio = AudioSystem(self.config_manager)
            self.audio.initialize()
            print("üéôÔ∏è Audio system initialized.")
        except Exception as e:
            self.failed_modules.append("audio")
            print(f"‚ö†Ô∏è Failed to init AudioSystem: {e}")

        try:
            self.stt = STTModule(self.config_manager)
            print("üó£Ô∏è STT module initialized.")
        except Exception as e:
            self.failed_modules.append("stt")
            print(f"‚ö†Ô∏è Failed to init STTModule: {e}")

        try:
            self.tts = TTSModule(self.config_manager)
            print("üîä TTS module initialized.")
        except Exception as e:
            self.failed_modules.append("tts")
            print(f"‚ö†Ô∏è Failed to init TTSModule: {e}")

        try:
            self.llm = LLMHandler(self.config_manager)
            print("üß† LLM handler initialized.")
        except Exception as e:
            self.failed_modules.append("llm")
            print(f"‚ö†Ô∏è Failed to init LLMHandler: {e}")

        try:
            self.executor = CommandExecutor(self.config_manager)
            print("ü§ñ Command executor initialized.")
        except Exception as e:
            self.failed_modules.append("executor")
            print(f"‚ö†Ô∏è Failed to init CommandExecutor: {e}")

        if self.failed_modules:
            print(f"‚ö†Ô∏è GEM started in degraded mode. Failed: {', '.join(self.failed_modules)}")

    # -------------------------------------------------------------------------
    # MAIN LOOP
    # -------------------------------------------------------------------------

    async def run(self, dry_run: bool = False):
        """
        Main asynchronous loop for wake-word detection, STT ‚Üí LLM ‚Üí TTS ‚Üí Command execution.
        """
        self.running = True
        self.greet_user()

        if dry_run:
            print("üîß Dry run mode: initialized all systems, skipping main loop.")
            return

        while self.running:
            try:
                if self.audio and self.audio.detect_wake_word():
                    print("‚ú® Wake word detected.")
                    query = None
                    if self.stt:
                        query = self.stt.listen_and_transcribe()

                    if not query:
                        print("ü§î No speech detected. Try again.")
                        continue

                    print(f"üìù You said: {query}")
                    response = None
                    if self.llm:
                        response = await self.llm.process_query(query)

                    if response:
                        if self.tts:
                            self.tts.speak(response)
                        if self.executor:
                            await self.executor.execute(response)
                        self.interaction_count += 1

                await asyncio.sleep(0.1)

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"‚ö†Ô∏è Error in main loop: {e}")
                await asyncio.sleep(1)

    # -------------------------------------------------------------------------
    # UTILITIES
    # -------------------------------------------------------------------------

    def greet_user(self):
        """Speak or print a welcome message."""
        msg = f"Welcome to GEM OS, profile [{self.profile}]."
        print(msg)
        try:
            if self.tts:
                self.tts.speak(msg)
        except Exception:
            pass

    def get_system_status(self) -> dict:
        """Return runtime system status summary."""
        uptime = time.time() - self.start_time
        return {
            "running": self.running,
            "uptime_sec": round(uptime, 2),
            "interactions": self.interaction_count,
            "profile": self.profile,
            "failed_modules": self.failed_modules,
        }

    def shutdown(self):
        """Gracefully shut down GEM subsystems."""
        print("\nüõë Shutting down GEM OS...")
        self.running = False
        # Cleanup subsystems
        for mod, name in [
            (self.audio, "audio"),
            (self.stt, "stt"),
            (self.tts, "tts"),
            (self.llm, "llm"),
            (self.executor, "executor"),
        ]:
            try:
                if mod:
                    mod.shutdown()
                    print(f"‚úÖ {name} stopped.")
            except Exception as e:
                print(f"‚ö†Ô∏è Error shutting down {name}: {e}")

        # Final report
        status = self.get_system_status()
        print("üìä Session Report:", status)

# =============================================================================
# SIGNAL HANDLING
# =============================================================================

def setup_signal_handlers(gem: GEM):
    """Setup Ctrl+C and termination signals for graceful shutdown."""
    loop = asyncio.get_event_loop()

    def handle_sigterm():
        gem.shutdown()
        loop.stop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, handle_sigterm)

# =============================================================================
# CLI ENTRYPOINT
# =============================================================================

def parse_args():
    parser = argparse.ArgumentParser(description="üíé GEM OS - Voice Assistant")
    parser.add_argument("--config", type=str, default="data/config.json", help="Path to config file")
    parser.add_argument("--profile", type=str, default="default", help="User profile to load")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--dry-run", action="store_true", help="Initialize systems but skip loop")
    return parser.parse_args()

def main():
    args = parse_args()
    gem = GEM(config_path=args.config, profile=args.profile, debug=args.debug)
    gem.initialize()

    loop = asyncio.get_event_loop()
    setup_signal_handlers(gem)

    try:
        loop.run_until_complete(gem.run(dry_run=args.dry_run))
    finally:
        gem.shutdown()

if __name__ == "__main__":
    main()
