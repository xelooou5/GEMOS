#!/usr/bin/env python3
"""
🔥 GEM OS - COMPLETE VOICE SYSTEM
Integrates STT + TTS for full voice interaction
"""

import asyncio
import logging
import numpy as np
import pyaudio
from pathlib import Path
from core.stt_module import STTModule
from core.tts_module import TTSModule
import os
from pathlib import Path

class SimpleConfig:
    def __init__(self):
        self.stt = type('STT', (), {'engine': 'whisper', 'model': 'base', 'language': 'pt-BR'})()
        self.tts = type('TTS', (), {'engine': 'pyttsx3', 'rate': 150, 'language': 'pt-BR'})()

ConfigManager = SimpleConfig

class VoiceSystem:
    """Complete voice system for GEM OS"""
    
    def __init__(self):
        self.config = ConfigManager()
        self.logger = logging.getLogger("VoiceSystem")
        
        self.stt = None
        self.tts = None
        self.audio = None
        self.is_listening = False
        self.wake_words = ["hey gem", "oi gem", "olá gem"]
        
    async def initialize(self):
        """Initialize complete voice system"""
        self.logger.info("🎤 Initializing GEM Voice System...")
        
        # Initialize STT
        self.stt = STTModule(self.config.stt, self.logger)
        await self.stt.initialize()
        
        # Initialize TTS  
        self.tts = TTSModule(self.config.tts, self.logger)
        await self.tts.initialize()
        
        # Initialize audio
        self.audio = pyaudio.PyAudio()
        
        self.logger.info("✅ Voice system ready")
        await self.tts.speak("GEM está pronto para ouvir você")
        
    async def listen_continuously(self):
        """Listen for wake words and commands"""
        self.logger.info("👂 Starting continuous listening...")
        
        stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=1024
        )
        
        try:
            while True:
                # Record audio chunk
                audio_data = stream.read(1024 * 4)  # 4 chunks
                audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
                
                # Transcribe
                result = await self.stt.transcribe(audio_np)
                text = result.get("text", "").lower()
                
                if text and any(wake_word in text for wake_word in self.wake_words):
                    self.logger.info(f"🔥 Wake word detected: {text}")
                    await self.handle_wake_word()
                    
                await asyncio.sleep(0.1)
                
        except KeyboardInterrupt:
            self.logger.info("Stopping voice system...")
        finally:
            stream.stop_stream()
            stream.close()
            
    async def handle_wake_word(self):
        """Handle wake word activation"""
        await self.tts.speak("Sim, como posso ajudar?")
        
        # Listen for command
        command = await self.listen_for_command()
        if command:
            await self.process_command(command)
            
    async def listen_for_command(self, timeout=5):
        """Listen for a command after wake word"""
        self.logger.info("🎯 Listening for command...")
        
        stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=1, 
            rate=16000,
            input=True,
            frames_per_buffer=1024
        )
        
        audio_buffer = []
        start_time = asyncio.get_event_loop().time()
        
        try:
            while (asyncio.get_event_loop().time() - start_time) < timeout:
                audio_data = stream.read(1024)
                audio_buffer.append(audio_data)
                await asyncio.sleep(0.01)
                
            # Process collected audio
            full_audio = b''.join(audio_buffer)
            audio_np = np.frombuffer(full_audio, dtype=np.int16).astype(np.float32) / 32768.0
            
            result = await self.stt.transcribe(audio_np)
            command = result.get("text", "")
            
            self.logger.info(f"Command received: {command}")
            return command
            
        finally:
            stream.stop_stream()
            stream.close()
            
    async def process_command(self, command):
        """Process voice command"""
        command_lower = command.lower()
        
        if "que horas são" in command_lower or "what time" in command_lower:
            from datetime import datetime
            now = datetime.now()
            time_str = now.strftime("%H:%M")
            await self.tts.speak(f"São {time_str}")
            
        elif "como está" in command_lower or "how are you" in command_lower:
            await self.tts.speak("Estou bem, obrigado por perguntar! Como posso ajudar você?")
            
        elif "ajuda" in command_lower or "help" in command_lower:
            await self.tts.speak("Posso ajudar com horário, lembretes, acessibilidade e muito mais. O que você precisa?")
            
        else:
            await self.tts.speak("Desculpe, não entendi. Pode repetir?")
            
    async def test_voice_system(self):
        """Test complete voice system"""
        self.logger.info("🧪 Testing voice system...")
        
        # Test TTS
        await self.tts.speak("Testando sistema de voz do GEM")
        
        # Test STT with sample
        test_audio = np.random.random(16000).astype(np.float32)  # 1 second
        result = await self.stt.transcribe(test_audio)
        self.logger.info(f"STT test result: {result}")
        
        return True
        
    def shutdown(self):
        """Shutdown voice system"""
        self.logger.info("🔇 Shutting down voice system...")
        
        if self.stt:
            self.stt.shutdown()
        if self.tts:
            self.tts.shutdown()
        if self.audio:
            self.audio.terminate()

async def main():
    """Main voice system entry point"""
    voice_system = VoiceSystem()
    
    try:
        await voice_system.initialize()
        await voice_system.test_voice_system()
        await voice_system.listen_continuously()
    except KeyboardInterrupt:
        pass
    finally:
        voice_system.shutdown()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())