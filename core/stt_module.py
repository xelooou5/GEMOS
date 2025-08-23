#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
💎 GEM OS - Speech-to-Text Module
Multi-engine STT with accessibility features
"""

import asyncio
import io
import logging
import tempfile
import wave
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional, Union, List
import numpy as np


class STTEngine(ABC):
    """Abstract base class for STT engines."""
    
    def __init__(self, config: Dict[str, Any], logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.is_initialized = False
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the STT engine."""
        pass
    
    @abstractmethod
    async def transcribe(self, audio_data: Union[bytes, np.ndarray]) -> Dict[str, Any]:
        """Transcribe audio data to text."""
        pass
    
    @abstractmethod
    def shutdown(self):
        """Shutdown the STT engine."""
        pass


class WhisperSTTEngine(STTEngine):
    """Whisper STT engine using faster-whisper."""
    
    def __init__(self, config: Dict[str, Any], logger: logging.Logger):
        super().__init__(config, logger)
        self.model = None
    
    async def initialize(self) -> bool:
        """Initialize Whisper model."""
        try:
            from faster_whisper import WhisperModel
            
            model_size = self.config.get('model', 'base')
            device = self.config.get('device', 'cpu')
            
            self.logger.info(f"Loading Whisper model: {model_size}")
            
            # Load model in a thread to avoid blocking
            loop = asyncio.get_event_loop()
            self.model = await loop.run_in_executor(
                None, 
                lambda: WhisperModel(model_size, device=device)
            )
            
            self.is_initialized = True
            self.logger.info("Whisper model loaded successfully")
            return True
        
        except ImportError:
            self.logger.error("faster-whisper not available")
            return False
        except Exception as e:
            self.logger.error(f"Error initializing Whisper: {e}")
            return False
    
    async def transcribe(self, audio_data: Union[bytes, np.ndarray]) -> Dict[str, Any]:
        """Transcribe audio using Whisper."""
        if not self.is_initialized:
            return {"text": "", "confidence": 0.0, "error": "Engine not initialized"}
        
        try:
            # Convert audio data to temporary file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                if isinstance(audio_data, bytes):
                    # Convert bytes to wav file
                    with wave.open(temp_file.name, 'wb') as wav_file:
                        wav_file.setnchannels(1)
                        wav_file.setsampwidth(2)  # 16-bit
                        wav_file.setframerate(16000)
                        wav_file.writeframes(audio_data)
                else:
                    # Convert numpy array to wav
                    import soundfile as sf
                    sf.write(temp_file.name, audio_data, 16000)
                
                # Transcribe in executor to avoid blocking with auto language detection
                loop = asyncio.get_event_loop()
                segments, info = await loop.run_in_executor(
                    None,
                    lambda: self.model.transcribe(
                        temp_file.name,
                        language=None,  # Auto-detect language
                        beam_size=5,
                        best_of=5
                    )
                )
                
                # Extract text and confidence
                text = ""
                total_confidence = 0.0
                segment_count = 0
                
                for segment in segments:
                    text += segment.text
                    total_confidence += segment.avg_logprob
                    segment_count += 1
                
                confidence = total_confidence / segment_count if segment_count > 0 else 0.0
                
                # Clean up temp file
                Path(temp_file.name).unlink(missing_ok=True)
                
                return {
                    "text": text.strip(),
                    "confidence": confidence,
                    "language": info.language,
                    "language_probability": info.language_probability
                }
        
        except Exception as e:
            self.logger.error(f"Whisper transcription error: {e}")
            return {"text": "", "confidence": 0.0, "error": str(e)}
    
    def shutdown(self):
        """Shutdown Whisper engine."""
        self.model = None
        self.is_initialized = False


class VoskSTTEngine(STTEngine):
    """Vosk STT engine for offline recognition."""
    
    def __init__(self, config: Dict[str, Any], logger: logging.Logger):
        super().__init__(config, logger)
        self.model = None
        self.recognizer = None
    
    async def initialize(self) -> bool:
        """Initialize Vosk model."""
        try:
            import vosk
            import json
            
            model_path = self.config.get('model_path', 'vosk-model-small-pt-0.3')
            
            if not Path(model_path).exists():
                self.logger.error(f"Vosk model not found: {model_path}")
                return False
            
            self.logger.info(f"Loading Vosk model: {model_path}")
            
            # Load model in executor
            loop = asyncio.get_event_loop()
            self.model = await loop.run_in_executor(
                None,
                lambda: vosk.Model(model_path)
            )
            
            self.recognizer = vosk.KaldiRecognizer(self.model, 16000)
            
            self.is_initialized = True
            self.logger.info("Vosk model loaded successfully")
            return True
        
        except ImportError:
            self.logger.error("Vosk not available")
            return False
        except Exception as e:
            self.logger.error(f"Error initializing Vosk: {e}")
            return False
    
    async def transcribe(self, audio_data: Union[bytes, np.ndarray]) -> Dict[str, Any]:
        """Transcribe audio using Vosk."""
        if not self.is_initialized:
            return {"text": "", "confidence": 0.0, "error": "Engine not initialized"}
        
        try:
            import json
            
            # Convert numpy array to bytes if needed
            if isinstance(audio_data, np.ndarray):
                audio_data = (audio_data * 32767).astype(np.int16).tobytes()
            
            # Process audio in executor
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._process_audio,
                audio_data
            )
            
            return result
        
        except Exception as e:
            self.logger.error(f"Vosk transcription error: {e}")
            return {"text": "", "confidence": 0.0, "error": str(e)}
    
    def _process_audio(self, audio_data: bytes) -> Dict[str, Any]:
        """Process audio data with Vosk."""
        import json
        
        # Feed audio data to recognizer
        self.recognizer.AcceptWaveform(audio_data)
        result = json.loads(self.recognizer.FinalResult())
        
        return {
            "text": result.get("text", ""),
            "confidence": result.get("confidence", 0.0)
        }
    
    def shutdown(self):
        """Shutdown Vosk engine."""
        self.model = None
        self.recognizer = None
        self.is_initialized = False


class GoogleSTTEngine(STTEngine):
    """Google Speech Recognition engine."""
    
    def __init__(self, config: Dict[str, Any], logger: logging.Logger):
        super().__init__(config, logger)
        self.recognizer = None
    
    async def initialize(self) -> bool:
        """Initialize Google STT."""
        try:
            import speech_recognition as sr
            
            self.recognizer = sr.Recognizer()
            
            # Configure recognizer
            self.recognizer.energy_threshold = self.config.get('energy_threshold', 300)
            self.recognizer.dynamic_energy_threshold = self.config.get('dynamic_energy_threshold', True)
            self.recognizer.pause_threshold = self.config.get('pause_threshold', 0.8)
            
            self.is_initialized = True
            self.logger.info("Google STT initialized")
            return True
        
        except ImportError:
            self.logger.error("speech_recognition not available")
            return False
        except Exception as e:
            self.logger.error(f"Error initializing Google STT: {e}")
            return False
    
    async def transcribe(self, audio_data: Union[bytes, np.ndarray]) -> Dict[str, Any]:
        """Transcribe audio using Google STT."""
        if not self.is_initialized:
            return {"text": "", "confidence": 0.0, "error": "Engine not initialized"}
        
        try:
            import speech_recognition as sr
            
            # Convert audio data to AudioData object
            if isinstance(audio_data, np.ndarray):
                audio_data = (audio_data * 32767).astype(np.int16).tobytes()
            
            audio_data_obj = sr.AudioData(audio_data, 16000, 2)
            
            # Transcribe in executor
            loop = asyncio.get_event_loop()
            text = await loop.run_in_executor(
                None,
                lambda: self.recognizer.recognize_google(
                    audio_data_obj,
                    language=self.config.get('language', 'pt-BR')
                )
            )
            
            return {
                "text": text,
                "confidence": 1.0  # Google doesn't provide confidence
            }
        
        except sr.UnknownValueError:
            return {"text": "", "confidence": 0.0, "error": "Could not understand audio"}
        except sr.RequestError as e:
            self.logger.error(f"Google STT request error: {e}")
            return {"text": "", "confidence": 0.0, "error": str(e)}
        except Exception as e:
            self.logger.error(f"Google STT error: {e}")
            return {"text": "", "confidence": 0.0, "error": str(e)}
    
    def shutdown(self):
        """Shutdown Google STT."""
        self.recognizer = None
        self.is_initialized = False


class STTModule:
    """Main STT module with multiple engine support."""
    
    def __init__(self, config, logger: Optional[logging.Logger] = None):
        self.config = config
        self.logger = logger or logging.getLogger("STTModule")
        
        self.engines: Dict[str, STTEngine] = {}
        self.current_engine: Optional[STTEngine] = None
        self.fallback_engines: List[str] = []
    
    async def initialize(self):
        """Initialize STT engines."""
        self.logger.info("Initializing STT module...")
        
        # Define available engines
        engine_classes = {
            'whisper': WhisperSTTEngine,
            'vosk': VoskSTTEngine,
            'google': GoogleSTTEngine
        }
        
        primary_engine = self.config.engine
        
        # Initialize primary engine
        if primary_engine in engine_classes:
            engine_class = engine_classes[primary_engine]
            engine = engine_class(self.config.__dict__, self.logger)
            
            if await engine.initialize():
                self.engines[primary_engine] = engine
                self.current_engine = engine
                self.logger.info(f"Primary STT engine '{primary_engine}' initialized")
            else:
                self.logger.warning(f"Failed to initialize primary engine '{primary_engine}'")
        
        # Initialize fallback engines
        for engine_name, engine_class in engine_classes.items():
            if engine_name != primary_engine and engine_name not in self.engines:
                engine = engine_class(self.config.__dict__, self.logger)
                
                if await engine.initialize():
                    self.engines[engine_name] = engine
                    self.fallback_engines.append(engine_name)
                    self.logger.info(f"Fallback STT engine '{engine_name}' initialized")
        
        if not self.current_engine:
            if self.fallback_engines:
                self.current_engine = self.engines[self.fallback_engines[0]]
                self.logger.info(f"Using fallback engine: {self.fallback_engines[0]}")
            else:
                raise RuntimeError("No STT engines could be initialized")
        
        self.logger.info("STT module initialization complete")
    
    async def transcribe(self, audio_data: Union[bytes, np.ndarray]) -> Dict[str, Any]:
        """Transcribe audio data to text with multilingual support."""
        if not self.current_engine:
            return {"text": "", "confidence": 0.0, "error": "No engine available"}
        
        # Try current engine
        result = await self.current_engine.transcribe(audio_data)
        
        # If current engine fails, try fallbacks
        if "error" in result and self.fallback_engines:
            self.logger.warning(f"Primary engine failed: {result.get('error')}")
            
            for fallback_name in self.fallback_engines:
                if fallback_name in self.engines:
                    self.logger.info(f"Trying fallback engine: {fallback_name}")
                    fallback_engine = self.engines[fallback_name]
                    result = await fallback_engine.transcribe(audio_data)
                    
                    if "error" not in result and result.get("text"):
                        self.logger.info(f"Fallback engine '{fallback_name}' succeeded")
                        break
        
        # Post-process result with language detection
        if result.get("text"):
            result["text"] = self._post_process_text(result["text"])
            result["detected_language"] = self._detect_language(result["text"])
        
        return result
    
    def _detect_language(self, text: str) -> str:
        """Simple language detection based on keywords."""
        text_lower = text.lower()
        
        # Portuguese indicators
        pt_keywords = ['oi', 'olá', 'que', 'como', 'está', 'são', 'horas', 'obrigado', 'por favor']
        # English indicators  
        en_keywords = ['hey', 'hi', 'what', 'how', 'are', 'you', 'time', 'thank', 'please']
        
        pt_score = sum(1 for word in pt_keywords if word in text_lower)
        en_score = sum(1 for word in en_keywords if word in text_lower)
        
        if pt_score > en_score:
            return 'pt-BR'
        elif en_score > pt_score:
            return 'en-US'
        else:
            return self.config.language  # Default to config language
    
    def _post_process_text(self, text: str) -> str:
        """Post-process transcribed text with multilingual support."""
        # Clean up text
        text = text.strip()
        
        # Remove extra whitespace
        import re
        text = re.sub(r'\s+', ' ', text)
        
        # Language-aware text processing
        text = self._apply_language_corrections(text)
        
        # Capitalize first letter
        if text:
            text = text[0].upper() + text[1:]
        
        return text
    
    def _apply_language_corrections(self, text: str) -> str:
        """Apply language-specific corrections."""
        # Common corrections for Portuguese
        pt_corrections = {
            'oi gem': 'Oi GEM',
            'hey gem': 'Hey GEM',
            'olá gem': 'Olá GEM',
            'que horas são': 'Que horas são',
            'como está': 'Como está'
        }
        
        # Common corrections for English
        en_corrections = {
            'hey gem': 'Hey GEM',
            'hi gem': 'Hi GEM',
            'what time': 'What time',
            'how are you': 'How are you'
        }
        
        text_lower = text.lower()
        
        # Apply corrections based on detected patterns
        for original, corrected in {**pt_corrections, **en_corrections}.items():
            if original in text_lower:
                text = text.replace(original, corrected)
                text = text.replace(original.title(), corrected)
        
        return text
    
    def switch_engine(self, engine_name: str) -> bool:
        """Switch to a different STT engine."""
        if engine_name in self.engines:
            self.current_engine = self.engines[engine_name]
            self.logger.info(f"Switched to STT engine: {engine_name}")
            return True
        else:
            self.logger.error(f"STT engine '{engine_name}' not available")
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
    
    async def test_transcription(self, test_audio_path: Optional[Path] = None):
        """Test transcription with sample audio."""
        self.logger.info("Testing STT transcription...")
        
        if test_audio_path and test_audio_path.exists():
            # Use provided test audio
            import soundfile as sf
            audio_data, sample_rate = sf.read(test_audio_path)
            
            if sample_rate != 16000:
                # Resample to 16kHz
                import librosa
                audio_data = librosa.resample(audio_data, orig_sr=sample_rate, target_sr=16000)
        else:
            # Generate test audio (silence)
            self.logger.warning("No test audio provided, using silence")
            audio_data = np.zeros(16000, dtype=np.float32)  # 1 second of silence
        
        # Test transcription
        result = await self.transcribe(audio_data)
        
        self.logger.info(f"Test result: {result}")
        return result
    
    def shutdown(self):
        """Shutdown all STT engines."""
        self.logger.info("Shutting down STT module...")
        
        for engine in self.engines.values():
            engine.shutdown()
        
        self.engines.clear()
        self.current_engine = None
        self.fallback_engines.clear()
        
        self.logger.info("STT module shutdown complete")