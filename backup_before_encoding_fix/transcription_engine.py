#!/usr/bin/env python3
# -*- coding: utf-8 -*-\r
"""\r
💎 GEM OS - Transcription Engine (core/transcription_engine.py)\r
Claude-style clarity + Gemini-style simplicity + my extra improvements.\r
\r
Responsibilities\r
----------------\r
- Orchestrates AudioSystem + WakeWord + STTModule\r
- Saves history into user_data.db\r
- Supports single-shot and streaming transcription\r
"""\r
\r
from __future__ import annotations\r
\r
import asyncio\r
import time\r
import logging\r
from typing import Optional, AsyncGenerator, Dict, Any\r
\r
class TranscriptionEngine:\r
    def __init__(self, config_manager, audio_system, stt_module, storage=None):\r
        self.config = config_manager\r
        self.audio = audio_system\r
        self.stt = stt_module\r
        self.storage = storage\r
        self.usage_count = 0\r
        self.last_latency = None\r
        self.logger = logging.getLogger("TranscriptionEngine")\r
\r
    # ------------------------------------------------------------------- Public\r
\r
    async def run_once(self, max_seconds: float = 8.0) -> Optional[Dict[str, Any]]:\r
        """\r
        Wait for wake word, record phrase, transcribe, save history.\r
        """\r
        self.logger.info("🎙️ Waiting for wake word... Say 'Hey GEM'.")\r
        if not self.audio.detect_wake_word():\r
            return None\r
\r
        pcm = self.audio.read_phrase(max_seconds=max_seconds)\r
        if not pcm:\r
            self.logger.warning("[TranscriptionEngine] No audio captured.")\r
            return None\r
        \r
        self.logger.info(f"Captured {len(pcm)} bytes of audio. Transcribing...")\r
        result = await self.stt.transcribe_audio(pcm)\r
        text = result.get("text", "")\r
        \r
        if text and self.storage:\r
            self.storage.save_history(text, "transcribed text", command="transcribe")\r
            self.logger.info(f"📜 Transcribed and saved: {text}")\r
            \r
        self.usage_count += 1\r
        self.last_latency = result.get("latency")\r
        \r
        return result\r
        \r
    async def stream_dictation(self, max_seconds: float = 60.0) -> AsyncGenerator[str, None]:\r
        """\r
        Transcribe continuously and yield a token at a time.\r
        Note: This is a placeholder and not fully implemented.\r
        """\r
        self.logger.info("🎙️ Dictation mode started. Speak now...")\r
        pcm = self.audio.read_phrase(max_seconds=max_seconds)\r
        if not pcm:\r
            yield "(no audio)"\r
            return\r
\r
        result = await self.stt.transcribe_audio(pcm)\r
        text = result.get("text", "")\r
        for token in text.split():\r
            yield token\r
\r
    # ------------------------------------------------------------------- Utils\r
\r
    def get_stats(self) -> dict:\r
        return {\r
            "usage_count": self.usage_count,\r
            "last_latency": self.last_latency,\r
        }\r
\r
    def shutdown(self) -> None:\r
        """Optional cleanup hook."""\r
        pass\r
\r
\r
# =============================================================================\r
# CLI Test\r
# =============================================================================\r
\r
if __name__ == "__main__":\r
    import asyncio\r
    from core.config_manager import ConfigManager\r
    from core.audio_system import AudioSystem\r
    from core.stt_module import STTModule\r
    from core.storage import Storage\r
\r
    cfg = ConfigManager()\r
    cfg.load()\r
    audio = AudioSystem(cfg)\r
    audio.initialize()\r
    stt = STTModule(cfg)\r
    db = Storage("data/user_data.db")\r
\r
    engine = TranscriptionEngine(cfg, audio, stt, db)\r
\r
    async def _test():\r
        print(await engine.run_once(max_seconds=3.0))\r
        audio.stop()\r
        db.shutdown()\r
    \r
    asyncio.run(_test())\r
