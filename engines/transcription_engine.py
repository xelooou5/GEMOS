#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GEM OS - Advanced Transcription Engine
High-accuracy speech recognition with multiple backends
"""

import asyncio
import logging
import numpy as np
from typing import Optional, Dict, Any, List, Tuple, Union
from dataclasses import dataclass
import tempfile
import os

@dataclass
class TranscriptionResult:
    text: str
    confidence: float
    language: str
    processing_time: float
    engine_used: str
    segments: List[Dict[str, Any]] = None

class TranscriptionEngine:
    def __init__(self, config: Optional[Dict[str, Any]] = None, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.config = config or {}
        
        # Engine preferences (in order of preference)
        self.engines = ["faster_whisper", "whisper", "vosk", "speech_recognition"]
        self.available_engines = []
        
        # Configuration
        self.language = self.config.get('language', 'pt')
        self.model_size = self.config.get('model_size', 'base')
        self.confidence_threshold = self.config.get('confidence_threshold', 0.7)
        
        # Engine instances
        self.faster_whisper_model = None
        self.whisper_model = None
        self.vosk_model = None
        self.sr_recognizer = None
        
        # Performance tracking
        self.transcription_stats = {
            "total_requests": 0,
            "successful_transcriptions": 0,
            "average_confidence": 0.0,
            "engine_usage": {}
        }
    
    async def initialize(self):
        """Initialize available transcription engines"""
        self.logger.info("Initializing transcription engines...")
        
        # Try to initialize Faster Whisper
        try:
            from faster_whisper import WhisperModel
            self.faster_whisper_model = WhisperModel(
                self.model_size, 
                device="cpu",  # Use CPU for compatibility
                compute_type="int8"
            )
            self.available_engines.append("faster_whisper")
            self.logger.info("✅ Faster Whisper initialized")
        except Exception as e:
            self.logger.warning(f"⚠️ Faster Whisper not available: {e}")
        
        # Try to initialize Whisper
        try:
            import whisper
            self.whisper_model = whisper.load_model(self.model_size)
            self.available_engines.append("whisper")
            self.logger.info("✅ Whisper initialized")
        except Exception as e:
            self.logger.warning(f"⚠️ Whisper not available: {e}")
        
        # Try to initialize Vosk
        try:
            import vosk
            import json
            
            # Download model if needed (simplified - in production, handle this better)
            model_path = f"vosk-model-{self.language}-0.22"
            if not os.path.exists(model_path):
                self.logger.info("Vosk model not found, using fallback")
            else:
                self.vosk_model = vosk.Model(model_path)
                self.available_engines.append("vosk")
                self.logger.info("✅ Vosk initialized")
        except Exception as e:
            self.logger.warning(f"⚠️ Vosk not available: {e}")
        
        # Try to initialize SpeechRecognition
        try:
            import speech_recognition as sr
            self.sr_recognizer = sr.Recognizer()
            self.available_engines.append("speech_recognition")
            self.logger.info("✅ SpeechRecognition initialized")
        except Exception as e:
            self.logger.warning(f"⚠️ SpeechRecognition not available: {e}")
        
        if not self.available_engines:
            raise RuntimeError("No transcription engines available")
        
        self.logger.info(f"Transcription engines ready: {', '.join(self.available_engines)}")
    
    async def transcribe(self, audio_data: Union[np.ndarray, bytes], 
                        engine: Optional[str] = None) -> TranscriptionResult:
        """Transcribe audio using the best available engine"""
        import time
        start_time = time.time()
        
        self.transcription_stats["total_requests"] += 1
        
        # Choose engine
        if engine and engine in self.available_engines:
            selected_engine = engine
        else:
            selected_engine = self.available_engines[0]  # Use first available
        
        try:
            result = await self._transcribe_with_engine(audio_data, selected_engine)
            result.processing_time = time.time() - start_time
            result.engine_used = selected_engine
            
            # Update statistics
            if result.confidence >= self.confidence_threshold:
                self.transcription_stats["successful_transcriptions"] += 1
            
            self._update_engine_stats(selected_engine, result.confidence)
            
            self.logger.debug(f"Transcription completed: '{result.text}' "
                            f"(confidence: {result.confidence:.2f}, "
                            f"engine: {selected_engine}, "
                            f"time: {result.processing_time:.2f}s)")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Transcription failed with {selected_engine}: {e}")
            
            # Try fallback engines
            for fallback_engine in self.available_engines:
                if fallback_engine != selected_engine:
                    try:
                        self.logger.info(f"Trying fallback engine: {fallback_engine}")
                        result = await self._transcribe_with_engine(audio_data, fallback_engine)
                        result.processing_time = time.time() - start_time
                        result.engine_used = fallback_engine
                        
                        self._update_engine_stats(fallback_engine, result.confidence)
                        return result
                        
                    except Exception as fallback_error:
                        self.logger.warning(f"Fallback engine {fallback_engine} failed: {fallback_error}")
                        continue
            
            # All engines failed
            raise RuntimeError("All transcription engines failed")
    
    async def _transcribe_with_engine(self, audio_data: Union[np.ndarray, bytes], 
                                    engine: str) -> TranscriptionResult:
        """Transcribe with specific engine"""
        
        if engine == "faster_whisper":
            return await self._transcribe_faster_whisper(audio_data)
        elif engine == "whisper":
            return await self._transcribe_whisper(audio_data)
        elif engine == "vosk":
            return await self._transcribe_vosk(audio_data)
        elif engine == "speech_recognition":
            return await self._transcribe_speech_recognition(audio_data)
        else:
            raise ValueError(f"Unknown engine: {engine}")
    
    async def _transcribe_faster_whisper(self, audio_data: Union[np.ndarray, bytes]) -> TranscriptionResult:
        """Transcribe using Faster Whisper"""
        if not self.faster_whisper_model:
            raise RuntimeError("Faster Whisper not initialized")
        
        # Convert audio data to temporary file if needed
        audio_file = await self._prepare_audio_file(audio_data)
        
        try:
            segments, info = self.faster_whisper_model.transcribe(
                audio_file,
                language=self.language,
                beam_size=5,
                best_of=5,
                temperature=0.0
            )
            
            # Combine segments
            text_parts = []
            segment_list = []
            total_confidence = 0
            segment_count = 0
            
            for segment in segments:
                text_parts.append(segment.text.strip())
                segment_list.append({
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text.strip()
                })
                # Faster Whisper doesn't provide confidence per segment
                # Use a default confidence based on model quality
                total_confidence += 0.85
                segment_count += 1
            
            text = " ".join(text_parts).strip()
            confidence = total_confidence / segment_count if segment_count > 0 else 0.0
            
            return TranscriptionResult(
                text=text,
                confidence=confidence,
                language=info.language,
                processing_time=0.0,  # Will be set by caller
                engine_used="faster_whisper",
                segments=segment_list
            )
            
        finally:
            if audio_file != audio_data:  # Clean up temp file
                try:
                    os.unlink(audio_file)
                except:
                    pass
    
    async def _transcribe_whisper(self, audio_data: Union[np.ndarray, bytes]) -> TranscriptionResult:
        """Transcribe using OpenAI Whisper"""
        if not self.whisper_model:
            raise RuntimeError("Whisper not initialized")
        
        # Convert audio data to numpy array if needed
        if isinstance(audio_data, bytes):
            # Convert bytes to numpy array (simplified)
            audio_array = np.frombuffer(audio_data, dtype=np.float32)
        else:
            audio_array = audio_data
        
        # Ensure audio is in the right format for Whisper
        if len(audio_array.shape) > 1:
            audio_array = audio_array.flatten()
        
        # Normalize audio
        audio_array = audio_array.astype(np.float32)
        if np.max(np.abs(audio_array)) > 0:
            audio_array = audio_array / np.max(np.abs(audio_array))
        
        result = self.whisper_model.transcribe(
            audio_array,
            language=self.language,
            fp16=False
        )
        
        # Extract segments if available
        segments = []
        if "segments" in result:
            for seg in result["segments"]:
                segments.append({
                    "start": seg.get("start", 0),
                    "end": seg.get("end", 0),
                    "text": seg.get("text", "").strip()
                })
        
        return TranscriptionResult(
            text=result["text"].strip(),
            confidence=0.8,  # Whisper doesn't provide confidence, use default
            language=result.get("language", self.language),
            processing_time=0.0,
            engine_used="whisper",
            segments=segments
        )
    
    async def _transcribe_vosk(self, audio_data: Union[np.ndarray, bytes]) -> TranscriptionResult:
        """Transcribe using Vosk"""
        if not self.vosk_model:
            raise RuntimeError("Vosk not initialized")
        
        import vosk
        import json
        
        # Create recognizer
        rec = vosk.KaldiRecognizer(self.vosk_model, 16000)
        
        # Convert audio to bytes if needed
        if isinstance(audio_data, np.ndarray):
            # Convert numpy array to bytes
            audio_bytes = (audio_data * 32767).astype(np.int16).tobytes()
        else:
            audio_bytes = audio_data
        
        # Process audio
        rec.AcceptWaveform(audio_bytes)
        result_json = rec.FinalResult()
        result_dict = json.loads(result_json)
        
        text = result_dict.get("text", "")
        confidence = result_dict.get("confidence", 0.0)
        
        return TranscriptionResult(
            text=text,
            confidence=confidence,
            language=self.language,
            processing_time=0.0,
            engine_used="vosk"
        )
    
    async def _transcribe_speech_recognition(self, audio_data: Union[np.ndarray, bytes]) -> TranscriptionResult:
        """Transcribe using SpeechRecognition library"""
        if not self.sr_recognizer:
            raise RuntimeError("SpeechRecognition not initialized")
        
        import speech_recognition as sr
        import io
        import wave
        
        # Convert audio to WAV format for SpeechRecognition
        audio_file = await self._prepare_audio_file(audio_data, format="wav")
        
        try:
            with sr.AudioFile(audio_file) as source:
                audio = self.sr_recognizer.record(source)
            
            # Try Google Speech Recognition (requires internet)
            try:
                text = self.sr_recognizer.recognize_google(audio, language=self.language)
                confidence = 0.75  # Default confidence for Google
            except sr.UnknownValueError:
                text = ""
                confidence = 0.0
            except sr.RequestError:
                # Fallback to offline recognition if available
                try:
                    text = self.sr_recognizer.recognize_sphinx(audio)
                    confidence = 0.6  # Lower confidence for offline
                except:
                    text = ""
                    confidence = 0.0
            
            return TranscriptionResult(
                text=text,
                confidence=confidence,
                language=self.language,
                processing_time=0.0,
                engine_used="speech_recognition"
            )
            
        finally:
            if audio_file != audio_data:
                try:
                    os.unlink(audio_file)
                except:
                    pass
    
    async def _prepare_audio_file(self, audio_data: Union[np.ndarray, bytes], 
                                format: str = "wav") -> str:
        """Prepare audio file for transcription"""
        if isinstance(audio_data, str) and os.path.exists(audio_data):
            return audio_data  # Already a file path
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(suffix=f".{format}", delete=False) as temp_file:
            temp_path = temp_file.name
            
            if isinstance(audio_data, bytes):
                temp_file.write(audio_data)
            elif isinstance(audio_data, np.ndarray):
                # Convert numpy array to WAV
                import soundfile as sf
                sf.write(temp_path, audio_data, 16000)
            
            return temp_path
    
    def _update_engine_stats(self, engine: str, confidence: float):
        """Update engine usage statistics"""
        if engine not in self.transcription_stats["engine_usage"]:
            self.transcription_stats["engine_usage"][engine] = {
                "count": 0,
                "total_confidence": 0.0
            }
        
        stats = self.transcription_stats["engine_usage"][engine]
        stats["count"] += 1
        stats["total_confidence"] += confidence
        
        # Update overall average confidence
        total_confidence = sum(
            engine_stats["total_confidence"] 
            for engine_stats in self.transcription_stats["engine_usage"].values()
        )
        total_count = sum(
            engine_stats["count"] 
            for engine_stats in self.transcription_stats["engine_usage"].values()
        )
        
        if total_count > 0:
            self.transcription_stats["average_confidence"] = total_confidence / total_count
    
    async def get_engine_status(self) -> Dict[str, Any]:
        """Get status of all transcription engines"""
        status = {
            "available_engines": self.available_engines,
            "preferred_engine": self.available_engines[0] if self.available_engines else None,
            "language": self.language,
            "model_size": self.model_size,
            "statistics": self.transcription_stats
        }
        
        # Add engine-specific status
        engine_details = {}
        for engine in self.available_engines:
            if engine == "faster_whisper" and self.faster_whisper_model:
                engine_details[engine] = {"status": "ready", "model": self.model_size}
            elif engine == "whisper" and self.whisper_model:
                engine_details[engine] = {"status": "ready", "model": self.model_size}
            elif engine == "vosk" and self.vosk_model:
                engine_details[engine] = {"status": "ready", "language": self.language}
            elif engine == "speech_recognition" and self.sr_recognizer:
                engine_details[engine] = {"status": "ready", "online_required": True}
        
        status["engine_details"] = engine_details
        return status
    
    async def benchmark_engines(self, test_audio: Union[np.ndarray, bytes]) -> Dict[str, Dict[str, Any]]:
        """Benchmark all available engines with test audio"""
        results = {}
        
        for engine in self.available_engines:
            try:
                result = await self._transcribe_with_engine(test_audio, engine)
                results[engine] = {
                    "text": result.text,
                    "confidence": result.confidence,
                    "processing_time": result.processing_time,
                    "success": True
                }
            except Exception as e:
                results[engine] = {
                    "error": str(e),
                    "success": False
                }
        
        return results
    
    def shutdown(self):
        """Cleanup transcription engine resources"""
        self.logger.info("Shutting down transcription engine...")
        
        # Clear models to free memory
        self.faster_whisper_model = None
        self.whisper_model = None
        self.vosk_model = None
        self.sr_recognizer = None
        
        self.logger.info("Transcription engine shutdown complete")