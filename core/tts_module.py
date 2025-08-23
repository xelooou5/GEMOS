#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
💎 GEM OS - Text-to-Speech Module
Multi-engine TTS with accessibility features
"""

import asyncio
import io
import logging
import tempfile
import threading
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional, List
import subprocess
import platform


class TTSEngine(ABC):
    """Abstract base class for TTS engines."""
    
    def __init__(self, config: Dict[str, Any], logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.is_initialized = False
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the TTS engine."""
        pass
    
    @abstractmethod
    async def speak(self, text: str) -> bool:
        """Speak the given text."""
        pass
    
    @abstractmethod
    async def save_audio(self, text: str, output_path: Path) -> bool:
        """Save speech audio to file."""
        pass
    
    @abstractmethod
    def shutdown(self):
        """Shutdown the TTS engine."""
        pass


class Pyttsx3TTSEngine(TTSEngine):
    """Pyttsx3 TTS engine for offline speech synthesis."""
    
    def __init__(self, config: Dict[str, Any], logger: logging.Logger):
        super().__init__(config, logger)
        self.engine = None
        self.lock = threading.Lock()
    
    async def initialize(self) -> bool:
        """Initialize pyttsx3 engine."""
        try:
            import pyttsx3
            
            # Initialize in executor to avoid blocking
            loop = asyncio.get_event_loop()
            self.engine = await loop.run_in_executor(None, pyttsx3.init)
            
            # Configure engine
            voices = self.engine.getProperty('voices')
            
            # Set voice based on config - prioritize calm female voices
            voice_id = self.config.get('voice')
            if voice_id:
                self.engine.setProperty('voice', voice_id)
            else:
                # Auto-select calm female voice for accessibility
                selected_voice = self._select_best_voice(voices)
                if selected_voice:
                    self.engine.setProperty('voice', selected_voice.id)
                    self.logger.info(f"Selected voice: {selected_voice.name}")
            
            # Set human-like speech parameters for accessibility
            rate = self.config.get('rate', 110)  # Much slower, more human pace
            volume = self.config.get('volume', 0.75)  # Gentle volume
            
            self.engine.setProperty('rate', rate)
            self.engine.setProperty('volume', volume)
            
            # Additional accessibility settings
            if hasattr(self.engine, 'setProperty'):
                try:
                    # Try to set additional properties for better accessibility
                    self.engine.setProperty('pitch', 50)  # Neutral pitch
                    self.engine.setProperty('inflection', 50)  # Natural inflection
                except:
                    pass  # Not all engines support these properties
            
            self.logger.info(f"Human-like speech configured: rate={rate}, volume={volume}")
            
            self.is_initialized = True
            self.logger.info("Pyttsx3 TTS engine initialized")
            return True
        
        except ImportError:
            self.logger.error("pyttsx3 not available")
            return False
        except Exception as e:
            self.logger.error(f"Error initializing pyttsx3: {e}")
            return False
    
    async def speak(self, text: str) -> bool:
        """Speak text using pyttsx3 with human-like enhancements and accessibility features."""
        if not self.is_initialized or not text.strip():
            return False
        
        try:
            # Enhance text for more human-like speech
            enhanced_text = self._enhance_text_for_speech(text)
            
            # Apply accessibility settings
            if self.config.get('human_like_speech', True):
                enhanced_text = self._apply_accessibility_enhancements(enhanced_text)
            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._speak_sync, enhanced_text)
            return True
        
        except Exception as e:
            self.logger.error(f"Pyttsx3 speak error: {e}")
            return False
    
    def _apply_accessibility_enhancements(self, text: str) -> str:
        """Apply accessibility-focused speech enhancements."""
        import re
        
        # Add extra pauses for screen reader compatibility
        text = re.sub(r'([.!?])\s*', r'\1 ... ', text)
        
        # Spell out abbreviations for clarity
        abbreviations = {
            'AI': 'A I',
            'TTS': 'T T S',
            'STT': 'S T T',
            'API': 'A P I',
            'URL': 'U R L',
            'USB': 'U S B'
        }
        
        for abbr, spelled in abbreviations.items():
            text = text.replace(abbr, spelled)
        
        # Add pauses before important information
        text = re.sub(r'\b(time|hora|temperature|temperatura|reminder|lembrete)\b', r'... \1', text, flags=re.IGNORECASE)
        
        return text
    
    def _speak_sync(self, text: str):
        """Synchronous speak method."""
        with self.lock:
            self.engine.say(text)
            self.engine.runAndWait()
    
    async def save_audio(self, text: str, output_path: Path) -> bool:
        """Save speech to audio file."""
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._save_sync, text, output_path)
            return True
        
        except Exception as e:
            self.logger.error(f"Pyttsx3 save error: {e}")
            return False
    
    def _save_sync(self, text: str, output_path: Path):
        """Synchronous save method."""
        with self.lock:
            self.engine.save_to_file(text, str(output_path))
            self.engine.runAndWait()
    
    def _select_best_voice(self, voices):
        """Select the best calm female voice for accessibility with language preference."""
        # Priority order for voice selection
        female_keywords = ['female', 'woman', 'zira', 'hazel', 'susan', 'samantha', 'karen', 'victoria']
        calm_keywords = ['calm', 'soft', 'gentle', 'natural', 'neural']
        
        # Language preferences based on config
        primary_lang = self.config.get('language', 'en-US')
        secondary_lang = self.config.get('secondary_language', 'pt-BR')
        
        # Score voices based on keywords and language
        scored_voices = []
        for voice in voices:
            score = 0
            name_lower = voice.name.lower()
            voice_id_lower = voice.id.lower()
            
            # Language preference scoring
            if primary_lang.startswith('en') and any(lang in voice_id_lower for lang in ['en', 'english', 'america', 'britain']):
                score += 20
            elif secondary_lang.startswith('pt') and any(lang in voice_id_lower for lang in ['pt', 'portuguese', 'brazil']):
                score += 15
            
            # Prefer female voices
            for keyword in female_keywords:
                if keyword in name_lower:
                    score += 10
            
            # Prefer calm/natural voices
            for keyword in calm_keywords:
                if keyword in name_lower:
                    score += 5
            
            # Avoid robotic voices
            if any(word in name_lower for word in ['robot', 'synthetic']):
                score -= 5
            
            scored_voices.append((voice, score))
        
        # Sort by score and return best voice
        scored_voices.sort(key=lambda x: x[1], reverse=True)
        return scored_voices[0][0] if scored_voices else None
    
    def shutdown(self):
        """Shutdown pyttsx3 engine."""
        if self.engine:
            try:
                self.engine.stop()
            except:
                pass
        self.engine = None
        self.is_initialized = False
    
    def _enhance_text_for_speech(self, text: str) -> str:
        """Enhance text for more natural, human-like speech with multilingual support."""
        import re
        
        # Detect language for appropriate enhancements
        is_portuguese = any(word in text.lower() for word in ['oi', 'olá', 'que', 'como', 'está', 'são'])
        
        # Add natural pauses after sentences
        text = re.sub(r'([.!?])\s*', r'\1... ', text)
        
        if is_portuguese:
            # Portuguese contractions and natural speech
            text = text.replace('Eu sou', 'Eu sou')
            text = text.replace('não posso', 'não posso')
            text = text.replace('você está', 'você tá')
            text = text.replace('para você', 'pra você')
        else:
            # English contractions and natural speech
            text = text.replace('I am', "I'm")
            text = text.replace('cannot', "can't")
            text = text.replace('do not', "don't")
            text = text.replace('will not', "won't")
            text = text.replace('you are', "you're")
        
        # Add breathing pauses for longer sentences
        if len(text) > 80:
            text = re.sub(r'(,)\s*', r'\1 ... ', text)
        
        # Add emphasis for important words
        text = re.sub(r'\b(GEM|gem)\b', r'GEM', text)
        
        # Slow down numbers for accessibility
        text = re.sub(r'(\d+)', r'\1 ', text)
        
        return text


class EspeakTTSEngine(TTSEngine):
    """Espeak TTS engine for lightweight speech synthesis."""
    
    def __init__(self, config: Dict[str, Any], logger: logging.Logger):
        super().__init__(config, logger)
        self.espeak_available = False
    
    async def initialize(self) -> bool:
        """Initialize espeak engine."""
        try:
            # Check if espeak is available
            result = subprocess.run(['espeak', '--version'], 
                                  capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                self.espeak_available = True
                self.is_initialized = True
                self.logger.info("Espeak TTS engine initialized")
                return True
            else:
                self.logger.error("Espeak not available")
                return False
        
        except (subprocess.TimeoutExpired, FileNotFoundError):
            self.logger.error("Espeak not found in system")
            return False
        except Exception as e:
            self.logger.error(f"Error initializing espeak: {e}")
            return False
    
    async def speak(self, text: str) -> bool:
        """Speak text using espeak."""
        if not self.is_initialized or not text.strip():
            return False
        
        try:
            # Build espeak command
            cmd = ['espeak']
            
            # Add language
            language = self.config.get('language', 'pt-br')
            cmd.extend(['-v', language])
            
            # Add speed
            speed = self.config.get('rate', 150)
            cmd.extend(['-s', str(speed)])
            
            # Add volume
            volume = int(self.config.get('volume', 0.9) * 100)
            cmd.extend(['-a', str(volume)])
            
            # Add text
            cmd.append(text)
            
            # Execute in executor
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: subprocess.run(cmd, capture_output=True, timeout=30)
            )
            
            return result.returncode == 0
        
        except Exception as e:
            self.logger.error(f"Espeak speak error: {e}")
            return False
    
    async def save_audio(self, text: str, output_path: Path) -> bool:
        """Save speech to audio file using espeak."""
        if not self.is_initialized or not text.strip():
            return False
        
        try:
            # Build espeak command for file output
            cmd = ['espeak']
            
            # Add language
            language = self.config.get('language', 'pt-br')
            cmd.extend(['-v', language])
            
            # Add speed
            speed = self.config.get('rate', 150)
            cmd.extend(['-s', str(speed)])
            
            # Add output file
            cmd.extend(['-w', str(output_path)])
            
            # Add text
            cmd.append(text)
            
            # Execute in executor
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: subprocess.run(cmd, capture_output=True, timeout=30)
            )
            
            return result.returncode == 0 and output_path.exists()
        
        except Exception as e:
            self.logger.error(f"Espeak save error: {e}")
            return False
    
    def shutdown(self):
        """Shutdown espeak engine."""
        self.is_initialized = False


class EdgeTTSEngine(TTSEngine):
    """Microsoft Edge TTS engine for high-quality speech."""
    
    def __init__(self, config: Dict[str, Any], logger: logging.Logger):
        super().__init__(config, logger)
        self.communicate = None
    
    async def initialize(self) -> bool:
        """Initialize Edge TTS."""
        try:
            import edge_tts
            self.communicate = edge_tts.Communicate
            
            self.is_initialized = True
            self.logger.info("Edge TTS engine initialized")
            return True
        
        except ImportError:
            self.logger.error("edge-tts not available")
            return False
        except Exception as e:
            self.logger.error(f"Error initializing Edge TTS: {e}")
            return False
    
    async def speak(self, text: str) -> bool:
        """Speak text using Edge TTS."""
        if not self.is_initialized or not text.strip():
            return False
        
        try:
            # Get voice
            voice = self._get_voice()
            
            # Create communicate object
            communicate = self.communicate(text, voice)
            
            # Generate and play audio
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        temp_file.write(chunk["data"])
                
                temp_path = Path(temp_file.name)
            
            # Play audio file
            await self._play_audio_file(temp_path)
            
            # Clean up
            temp_path.unlink(missing_ok=True)
            
            return True
        
        except Exception as e:
            self.logger.error(f"Edge TTS speak error: {e}")
            return False
    
    async def save_audio(self, text: str, output_path: Path) -> bool:
        """Save speech to audio file using Edge TTS."""
        if not self.is_initialized or not text.strip():
            return False
        
        try:
            # Get voice
            voice = self._get_voice()
            
            # Create communicate object
            communicate = self.communicate(text, voice)
            
            # Save audio
            await communicate.save(str(output_path))
            
            return output_path.exists()
        
        except Exception as e:
            self.logger.error(f"Edge TTS save error: {e}")
            return False
    
    def _get_voice(self) -> str:
        """Get appropriate calm female voice for Edge TTS with language priority."""
        primary_language = self.config.get('language', 'en-US')
        secondary_language = self.config.get('secondary_language', 'pt-BR')
        gender = self.config.get('gender', 'female').lower()
        
        # Voice mapping with calm, natural female voices prioritized
        voice_map = {
            'en-US': {
                'female': 'en-US-AriaNeural',  # Calm, professional female voice
                'male': 'en-US-GuyNeural'
            },
            'pt-BR': {
                'female': 'pt-BR-FranciscaNeural',  # Calm, natural Brazilian voice
                'male': 'pt-BR-AntonioNeural'
            },
            'es-ES': {
                'female': 'es-ES-ElviraNeural',  # Gentle Spanish female voice
                'male': 'es-ES-AlvaroNeural'
            }
        }
        
        # Try primary language first, then secondary
        if primary_language in voice_map:
            return voice_map[primary_language].get(gender, voice_map[primary_language]['female'])
        elif secondary_language in voice_map:
            return voice_map[secondary_language].get(gender, voice_map[secondary_language]['female'])
        else:
            return 'en-US-AriaNeural'  # Default to calm English voice
    
    async def _play_audio_file(self, file_path: Path):
        """Play audio file."""
        try:
            if platform.system() == "Linux":
                subprocess.run(['aplay', str(file_path)], check=True)
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(['afplay', str(file_path)], check=True)
            elif platform.system() == "Windows":
                import winsound
                winsound.PlaySound(str(file_path), winsound.SND_FILENAME)
        
        except Exception as e:
            self.logger.error(f"Error playing audio: {e}")
    
    def shutdown(self):
        """Shutdown Edge TTS engine."""
        self.is_initialized = False


class GTTSEngine(TTSEngine):
    """Google Text-to-Speech engine."""
    
    def __init__(self, config: Dict[str, Any], logger: logging.Logger):
        super().__init__(config, logger)
    
    async def initialize(self) -> bool:
        """Initialize gTTS."""
        try:
            from gtts import gTTS
            self.gtts_class = gTTS
            
            self.is_initialized = True
            self.logger.info("gTTS engine initialized")
            return True
        
        except ImportError:
            self.logger.error("gTTS not available")
            return False
        except Exception as e:
            self.logger.error(f"Error initializing gTTS: {e}")
            return False
    
    async def speak(self, text: str) -> bool:
        """Speak text using gTTS."""
        if not self.is_initialized or not text.strip():
            return False
        
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
                temp_path = Path(temp_file.name)
            
            # Generate speech
            await self.save_audio(text, temp_path)
            
            # Play audio
            await self._play_audio_file(temp_path)
            
            # Clean up
            temp_path.unlink(missing_ok=True)
            
            return True
        
        except Exception as e:
            self.logger.error(f"gTTS speak error: {e}")
            return False
    
    async def save_audio(self, text: str, output_path: Path) -> bool:
        """Save speech to audio file using gTTS."""
        if not self.is_initialized or not text.strip():
            return False
        
        try:
            language = self.config.get('language', 'pt-br')
            
            # Create gTTS object
            tts = self.gtts_class(text=text, lang=language, slow=False)
            
            # Save in executor
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, tts.save, str(output_path))
            
            return output_path.exists()
        
        except Exception as e:
            self.logger.error(f"gTTS save error: {e}")
            return False
    
    async def _play_audio_file(self, file_path: Path):
        """Play audio file."""
        try:
            if platform.system() == "Linux":
                subprocess.run(['mpg123', str(file_path)], check=True)
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(['afplay', str(file_path)], check=True)
            elif platform.system() == "Windows":
                import winsound
                winsound.PlaySound(str(file_path), winsound.SND_FILENAME)
        
        except Exception as e:
            self.logger.error(f"Error playing audio: {e}")
    
    def shutdown(self):
        """Shutdown gTTS engine."""
        self.is_initialized = False


class TTSModule:
    """Main TTS module with multiple engine support."""
    
    def __init__(self, config, logger: Optional[logging.Logger] = None):
        self.config = config
        self.logger = logger or logging.getLogger("TTSModule")
        
        self.engines: Dict[str, TTSEngine] = {}
        self.current_engine: Optional[TTSEngine] = None
        self.fallback_engines: List[str] = []
    
    async def initialize(self):
        """Initialize TTS engines."""
        self.logger.info("Initializing TTS module...")
        
        # Define available engines
        engine_classes = {
            'pyttsx3': Pyttsx3TTSEngine,
            'espeak': EspeakTTSEngine,
            'edge-tts': EdgeTTSEngine,
            'gtts': GTTSEngine
        }
        
        primary_engine = self.config.engine
        
        # Initialize primary engine
        if primary_engine in engine_classes:
            engine_class = engine_classes[primary_engine]
            engine = engine_class(self.config.__dict__, self.logger)
            
            if await engine.initialize():
                self.engines[primary_engine] = engine
                self.current_engine = engine
                self.logger.info(f"Primary TTS engine '{primary_engine}' initialized")
            else:
                self.logger.warning(f"Failed to initialize primary engine '{primary_engine}'")
        
        # Initialize fallback engines
        for engine_name, engine_class in engine_classes.items():
            if engine_name != primary_engine and engine_name not in self.engines:
                engine = engine_class(self.config.__dict__, self.logger)
                
                if await engine.initialize():
                    self.engines[engine_name] = engine
                    self.fallback_engines.append(engine_name)
                    self.logger.info(f"Fallback TTS engine '{engine_name}' initialized")
        
        if not self.current_engine:
            if self.fallback_engines:
                self.current_engine = self.engines[self.fallback_engines[0]]
                self.logger.info(f"Using fallback engine: {self.fallback_engines[0]}")
            else:
                raise RuntimeError("No TTS engines could be initialized")
        
        self.logger.info("TTS module initialization complete")
    
    async def speak(self, text: str) -> bool:
        """Speak text using current engine."""
        if not self.current_engine or not text.strip():
            return False
        
        # Try current engine
        success = await self.current_engine.speak(text)
        
        # If current engine fails, try fallbacks
        if not success and self.fallback_engines:
            self.logger.warning("Primary TTS engine failed, trying fallbacks")
            
            for fallback_name in self.fallback_engines:
                if fallback_name in self.engines:
                    self.logger.info(f"Trying fallback TTS engine: {fallback_name}")
                    fallback_engine = self.engines[fallback_name]
                    success = await fallback_engine.speak(text)
                    
                    if success:
                        self.logger.info(f"Fallback engine '{fallback_name}' succeeded")
                        break
        
        return success
    
    async def save_audio(self, text: str, output_path: Path) -> bool:
        """Save speech to audio file."""
        if not self.current_engine or not text.strip():
            return False
        
        return await self.current_engine.save_audio(text, output_path)
    
    def switch_engine(self, engine_name: str) -> bool:
        """Switch to a different TTS engine."""
        if engine_name in self.engines:
            self.current_engine = self.engines[engine_name]
            self.logger.info(f"Switched to TTS engine: {engine_name}")
            return True
        else:
            self.logger.error(f"TTS engine '{engine_name}' not available")
            return False
    
    def get_available_engines(self) -> List[str]:
        """Get list of available engines."""
        return list(self.engines.keys())
    
    def get_current_engine(self) -> Optional[str]:
        """Get current engine name."""
        for name, engine in self.engines.items():
            if engine == self.current_engine:
                return name
        return None
    
    async def test_speech(self, test_text: str = None):
        """Test TTS with multilingual sample text."""
        self.logger.info("Testing TTS speech...")
        
        if not test_text:
            # Choose test text based on primary language
            primary_lang = self.config.language if hasattr(self.config, 'language') else 'en-US'
            
            if primary_lang.startswith('pt'):
                test_text = "Olá, este é um teste do sistema de síntese de voz do GEM. Como você está hoje?"
            else:
                test_text = "Hello, this is a test of the GEM voice synthesis system. How are you today?"
        
        success = await self.speak(test_text)
        
        if success:
            self.logger.info("✅ TTS test successful")
        else:
            self.logger.error("❌ TTS test failed")
        
        return success
    
    def shutdown(self):
        """Shutdown all TTS engines."""
        self.logger.info("Shutting down TTS module...")
        
        for engine in self.engines.values():
            engine.shutdown()
        
        self.engines.clear()
        self.current_engine = None
        self.fallback_engines.clear()
        
        self.logger.info("TTS module shutdown complete")