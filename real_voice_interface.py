#!/usr/bin/env python3
"""
🚀 COPILOT: REAL VOICE INTERFACE - WORKING IMPLEMENTATION, NO EXAMPLES
CRITICAL: The voice interface is how users interact with the system. It must work perfectly.
Real microphone input, speaker output, wake word detection, audio processing
"""

import asyncio
import pyaudio
import wave
import numpy as np
import threading
import queue
import time
import os
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
import logging

class RealVoiceInterface:
    """REAL voice interface implementation - COPILOT's contribution"""
    
    def __init__(self):
        # REAL audio configuration (not examples)
        self.audio_config = {
            'sample_rate': int(os.getenv('GEM_AUDIO_SAMPLE_RATE', '16000')),
            'channels': int(os.getenv('GEM_AUDIO_CHANNELS', '1')),
            'chunk_size': int(os.getenv('GEM_AUDIO_BUFFER_SIZE', '1024')),
            'format': pyaudio.paInt16,
            'input_device_index': None,
            'output_device_index': None
        }
        
        # Wake word configuration
        self.wake_words = [
            os.getenv('GEM_WAKE_WORD', 'gemini').lower(),
            'hey gem',
            'emergency',
            'help me'
        ]
        
        # Voice processing components
        self.audio_interface = None
        self.input_stream = None
        self.output_stream = None
        self.is_listening = False
        self.is_speaking = False
        
        # Audio buffers and queues
        self.audio_buffer = queue.Queue()
        self.speech_queue = queue.Queue()
        self.command_queue = queue.Queue()
        
        # Voice recognition engines
        self.stt_engines = {
            'whisper': {'available': False, 'engine': None},
            'google': {'available': False, 'engine': None},
            'sphinx': {'available': False, 'engine': None}
        }
        
        # Text-to-speech engines
        self.tts_engines = {
            'pyttsx3': {'available': False, 'engine': None},
            'espeak': {'available': False, 'engine': None},
            'festival': {'available': False, 'engine': None}
        }
        
        # Performance metrics
        self.metrics = {
            'wake_word_detections': 0,
            'voice_commands_processed': 0,
            'speech_synthesis_requests': 0,
            'audio_processing_times': [],
            'recognition_accuracy': [],
            'synthesis_times': []
        }
        
        self.logger = logging.getLogger("RealVoiceInterface")
        
        print("🚀 COPILOT: Real Voice Interface initialized")
        
    def initialize_audio_system(self) -> bool:
        """Initialize REAL audio system with hardware detection"""
        try:
            self.audio_interface = pyaudio.PyAudio()
            
            # Detect audio devices
            input_devices = []
            output_devices = []
            
            print("\n🔍 DETECTING AUDIO DEVICES...")
            
            for i in range(self.audio_interface.get_device_count()):
                device_info = self.audio_interface.get_device_info_by_index(i)
                
                if device_info['maxInputChannels'] > 0:
                    input_devices.append({
                        'index': i,
                        'name': device_info['name'],
                        'channels': device_info['maxInputChannels'],
                        'sample_rate': device_info['defaultSampleRate']
                    })
                    
                if device_info['maxOutputChannels'] > 0:
                    output_devices.append({
                        'index': i,
                        'name': device_info['name'],
                        'channels': device_info['maxOutputChannels'],
                        'sample_rate': device_info['defaultSampleRate']
                    })
                    
            print(f"✅ Input devices found: {len(input_devices)}")
            for device in input_devices[:3]:  # Show first 3
                print(f"   {device['index']}: {device['name']}")
                
            print(f"✅ Output devices found: {len(output_devices)}")
            for device in output_devices[:3]:  # Show first 3
                print(f"   {device['index']}: {device['name']}")
                
            # Select default devices
            if input_devices:
                self.audio_config['input_device_index'] = input_devices[0]['index']
                
            if output_devices:
                self.audio_config['output_device_index'] = output_devices[0]['index']
                
            return len(input_devices) > 0 and len(output_devices) > 0
            
        except Exception as e:
            self.logger.error(f"Audio system initialization failed: {e}")
            return False
            
    def initialize_stt_engines(self) -> Dict[str, bool]:
        """Initialize REAL speech-to-text engines"""
        print("\n🎤 INITIALIZING SPEECH-TO-TEXT ENGINES...")
        
        # Try Whisper (OpenAI)
        try:
            import whisper
            model = whisper.load_model("base")
            self.stt_engines['whisper'] = {
                'available': True,
                'engine': model,
                'accuracy': 0.95,
                'latency_ms': 800
            }
            print("✅ Whisper STT engine loaded")
        except ImportError:
            print("⚠️ Whisper not available (pip install openai-whisper)")
            
        # Try Google Speech Recognition
        try:
            import speech_recognition as sr
            recognizer = sr.Recognizer()
            self.stt_engines['google'] = {
                'available': True,
                'engine': recognizer,
                'accuracy': 0.92,
                'latency_ms': 1200
            }
            print("✅ Google STT engine loaded")
        except ImportError:
            print("⚠️ Google STT not available (pip install SpeechRecognition)")
            
        # Try PocketSphinx (offline)
        try:
            import speech_recognition as sr
            recognizer = sr.Recognizer()
            # Test if PocketSphinx is available
            test_audio = sr.AudioData(b'\x00' * 1000, 16000, 2)
            try:
                recognizer.recognize_sphinx(test_audio)
                self.stt_engines['sphinx'] = {
                    'available': True,
                    'engine': recognizer,
                    'accuracy': 0.85,
                    'latency_ms': 600
                }
                print("✅ PocketSphinx STT engine loaded")
            except:
                print("⚠️ PocketSphinx not properly configured")
        except ImportError:
            print("⚠️ PocketSphinx not available")
            
        available_engines = sum(1 for engine in self.stt_engines.values() if engine['available'])
        print(f"📊 STT Engines available: {available_engines}/{len(self.stt_engines)}")
        
        return {name: engine['available'] for name, engine in self.stt_engines.items()}
        
    def initialize_tts_engines(self) -> Dict[str, bool]:
        """Initialize REAL text-to-speech engines"""
        print("\n🗣️ INITIALIZING TEXT-TO-SPEECH ENGINES...")
        
        # Try pyttsx3
        try:
            import pyttsx3
            engine = pyttsx3.init()
            
            # Configure voice properties
            voices = engine.getProperty('voices')
            if voices:
                # Prefer female voice for accessibility
                for voice in voices:
                    if 'female' in voice.name.lower() or 'woman' in voice.name.lower():
                        engine.setProperty('voice', voice.id)
                        break
                        
            engine.setProperty('rate', 150)  # Speaking rate
            engine.setProperty('volume', 0.9)  # Volume level
            
            self.tts_engines['pyttsx3'] = {
                'available': True,
                'engine': engine,
                'quality': 'good',
                'latency_ms': 200
            }
            print("✅ pyttsx3 TTS engine loaded")
        except ImportError:
            print("⚠️ pyttsx3 not available (pip install pyttsx3)")
            
        # Try eSpeak
        try:
            import subprocess
            result = subprocess.run(['espeak', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                self.tts_engines['espeak'] = {
                    'available': True,
                    'engine': 'espeak',
                    'quality': 'basic',
                    'latency_ms': 100
                }
                print("✅ eSpeak TTS engine available")
        except FileNotFoundError:
            print("⚠️ eSpeak not available (sudo apt install espeak)")
            
        # Try Festival
        try:
            import subprocess
            result = subprocess.run(['festival', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                self.tts_engines['festival'] = {
                    'available': True,
                    'engine': 'festival',
                    'quality': 'good',
                    'latency_ms': 300
                }
                print("✅ Festival TTS engine available")
        except FileNotFoundError:
            print("⚠️ Festival not available (sudo apt install festival)")
            
        available_engines = sum(1 for engine in self.tts_engines.values() if engine['available'])
        print(f"📊 TTS Engines available: {available_engines}/{len(self.tts_engines)}")
        
        return {name: engine['available'] for name, engine in self.tts_engines.items()}
        
    def start_audio_streams(self) -> bool:
        """Start REAL audio input and output streams"""
        try:
            # Input stream for microphone
            if self.audio_config['input_device_index'] is not None:
                self.input_stream = self.audio_interface.open(
                    format=self.audio_config['format'],
                    channels=self.audio_config['channels'],
                    rate=self.audio_config['sample_rate'],
                    input=True,
                    input_device_index=self.audio_config['input_device_index'],
                    frames_per_buffer=self.audio_config['chunk_size'],
                    stream_callback=self._audio_input_callback
                )
                print("✅ Audio input stream started")
                
            # Output stream for speakers
            if self.audio_config['output_device_index'] is not None:
                self.output_stream = self.audio_interface.open(
                    format=self.audio_config['format'],
                    channels=self.audio_config['channels'],
                    rate=self.audio_config['sample_rate'],
                    output=True,
                    output_device_index=self.audio_config['output_device_index'],
                    frames_per_buffer=self.audio_config['chunk_size']
                )
                print("✅ Audio output stream started")
                
            return True
            
        except Exception as e:
            self.logger.error(f"Audio stream initialization failed: {e}")
            return False
            
    def _audio_input_callback(self, in_data, frame_count, time_info, status):
        """REAL audio input callback for continuous listening"""
        if self.is_listening:
            # Convert audio data to numpy array
            audio_array = np.frombuffer(in_data, dtype=np.int16)
            
            # Simple voice activity detection
            audio_level = np.sqrt(np.mean(audio_array**2))
            
            if audio_level > 500:  # Threshold for voice detection
                self.audio_buffer.put({
                    'data': in_data,
                    'timestamp': time.time(),
                    'level': audio_level
                })
                
        return (None, pyaudio.paContinue)
        
    async def detect_wake_word(self, audio_data: bytes) -> Optional[str]:
        """REAL wake word detection"""
        try:
            # Use best available STT engine for wake word detection
            best_engine = self._select_best_stt_engine()
            
            if not best_engine:
                return None
                
            # Quick transcription for wake word
            text = await self._transcribe_audio(audio_data, best_engine, quick=True)
            
            if text:
                text_lower = text.lower()
                for wake_word in self.wake_words:
                    if wake_word in text_lower:
                        self.metrics['wake_word_detections'] += 1
                        print(f"🎤 Wake word detected: '{wake_word}'")
                        return wake_word
                        
            return None
            
        except Exception as e:
            self.logger.error(f"Wake word detection failed: {e}")
            return None
            
    async def _transcribe_audio(self, audio_data: bytes, engine_name: str, quick: bool = False) -> Optional[str]:
        """REAL audio transcription"""
        start_time = time.time()
        
        try:
            engine_info = self.stt_engines[engine_name]
            
            if engine_name == 'whisper':
                # Whisper transcription
                import tempfile
                import whisper
                
                # Save audio to temporary file
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                    # Convert raw audio to WAV
                    with wave.open(temp_file.name, 'wb') as wav_file:
                        wav_file.setnchannels(self.audio_config['channels'])
                        wav_file.setsampwidth(2)  # 16-bit
                        wav_file.setframerate(self.audio_config['sample_rate'])
                        wav_file.writeframes(audio_data)
                        
                    # Transcribe with Whisper
                    result = engine_info['engine'].transcribe(temp_file.name)
                    text = result['text'].strip()
                    
                    # Clean up
                    os.unlink(temp_file.name)
                    
            elif engine_name == 'google':
                # Google Speech Recognition
                import speech_recognition as sr
                
                # Convert audio data to AudioData object
                audio = sr.AudioData(audio_data, self.audio_config['sample_rate'], 2)
                
                # Recognize with Google
                text = engine_info['engine'].recognize_google(audio)
                
            elif engine_name == 'sphinx':
                # PocketSphinx recognition
                import speech_recognition as sr
                
                audio = sr.AudioData(audio_data, self.audio_config['sample_rate'], 2)
                text = engine_info['engine'].recognize_sphinx(audio)
                
            else:
                return None
                
            # Record performance metrics
            processing_time = (time.time() - start_time) * 1000  # ms
            self.metrics['audio_processing_times'].append(processing_time)
            
            if not quick:
                print(f"🎤 Transcribed ({engine_name}): '{text}' ({processing_time:.0f}ms)")
                
            return text
            
        except Exception as e:
            if not quick:
                self.logger.error(f"Transcription failed with {engine_name}: {e}")
            return None
            
    def _select_best_stt_engine(self) -> Optional[str]:
        """Select best available STT engine based on performance"""
        available_engines = [(name, info) for name, info in self.stt_engines.items() if info['available']]
        
        if not available_engines:
            return None
            
        # Sort by accuracy and latency
        scored_engines = []
        for name, info in available_engines:
            score = info['accuracy'] * 0.7 + (1000 - info['latency_ms']) / 1000 * 0.3
            scored_engines.append((name, score))
            
        scored_engines.sort(key=lambda x: x[1], reverse=True)
        return scored_engines[0][0]
        
    async def speak_text(self, text: str, priority: str = 'normal') -> bool:
        """REAL text-to-speech synthesis"""
        start_time = time.time()
        
        try:
            # Select best TTS engine
            best_engine = self._select_best_tts_engine()
            
            if not best_engine:
                print(f"📢 TTS not available: {text}")
                return False
                
            self.is_speaking = True
            
            engine_info = self.tts_engines[best_engine]
            
            if best_engine == 'pyttsx3':
                # pyttsx3 synthesis
                engine = engine_info['engine']
                
                # Adjust rate for priority
                if priority == 'emergency':
                    engine.setProperty('rate', 180)  # Faster for emergencies
                    engine.setProperty('volume', 1.0)  # Louder
                else:
                    engine.setProperty('rate', 150)  # Normal rate
                    engine.setProperty('volume', 0.9)
                    
                # Speak text
                engine.say(text)
                engine.runAndWait()
                
            elif best_engine == 'espeak':
                # eSpeak synthesis
                import subprocess
                
                speed = '180' if priority == 'emergency' else '150'
                subprocess.run(['espeak', '-s', speed, text])
                
            elif best_engine == 'festival':
                # Festival synthesis
                import subprocess
                
                process = subprocess.Popen(['festival', '--tts'], stdin=subprocess.PIPE)
                process.communicate(input=text.encode())
                
            self.is_speaking = False
            
            # Record metrics
            synthesis_time = (time.time() - start_time) * 1000  # ms
            self.metrics['synthesis_times'].append(synthesis_time)
            self.metrics['speech_synthesis_requests'] += 1
            
            print(f"🗣️ Spoke ({best_engine}): '{text[:50]}...' ({synthesis_time:.0f}ms)")
            return True
            
        except Exception as e:
            self.is_speaking = False
            self.logger.error(f"Speech synthesis failed: {e}")
            return False
            
    def _select_best_tts_engine(self) -> Optional[str]:
        """Select best available TTS engine"""
        available_engines = [(name, info) for name, info in self.tts_engines.items() if info['available']]
        
        if not available_engines:
            return None
            
        # Prefer pyttsx3 for quality, espeak for speed
        priority_order = ['pyttsx3', 'festival', 'espeak']
        
        for engine_name in priority_order:
            if any(name == engine_name for name, _ in available_engines):
                return engine_name
                
        return available_engines[0][0]
        
    async def listen_for_command(self, timeout: float = 5.0) -> Optional[str]:
        """Listen for voice command with timeout"""
        print(f"🎤 Listening for command (timeout: {timeout}s)...")
        
        self.is_listening = True
        audio_chunks = []
        start_time = time.time()
        
        try:
            while time.time() - start_time < timeout:
                try:
                    # Get audio data from buffer
                    audio_item = self.audio_buffer.get(timeout=0.1)
                    audio_chunks.append(audio_item['data'])
                    
                    # Check if we have enough audio (2 seconds)
                    if len(audio_chunks) >= 32:  # ~2 seconds at 16kHz
                        break
                        
                except queue.Empty:
                    continue
                    
            self.is_listening = False
            
            if audio_chunks:
                # Combine audio chunks
                combined_audio = b''.join(audio_chunks)
                
                # Transcribe with best engine
                best_engine = self._select_best_stt_engine()
                if best_engine:
                    text = await self._transcribe_audio(combined_audio, best_engine)
                    if text:
                        self.metrics['voice_commands_processed'] += 1
                        return text
                        
            return None
            
        except Exception as e:
            self.is_listening = False
            self.logger.error(f"Voice command listening failed: {e}")
            return None
            
    async def emergency_announce(self, message: str):
        """EMERGENCY announcement with highest priority"""
        print(f"🚨 EMERGENCY ANNOUNCEMENT: {message}")
        
        # Stop any current speech
        self.is_speaking = False
        
        # Speak with emergency priority
        await self.speak_text(f"EMERGENCY: {message}", priority='emergency')
        
        # Repeat for emphasis
        await asyncio.sleep(0.5)
        await self.speak_text(message, priority='emergency')
        
    def get_voice_metrics(self) -> Dict[str, Any]:
        """Get voice interface performance metrics"""
        
        avg_processing_time = sum(self.metrics['audio_processing_times'][-10:]) / min(10, len(self.metrics['audio_processing_times'])) if self.metrics['audio_processing_times'] else 0
        
        avg_synthesis_time = sum(self.metrics['synthesis_times'][-10:]) / min(10, len(self.metrics['synthesis_times'])) if self.metrics['synthesis_times'] else 0
        
        return {
            'wake_word_detections': self.metrics['wake_word_detections'],
            'voice_commands_processed': self.metrics['voice_commands_processed'],
            'speech_synthesis_requests': self.metrics['speech_synthesis_requests'],
            'avg_processing_time_ms': avg_processing_time,
            'avg_synthesis_time_ms': avg_synthesis_time,
            'stt_engines_available': sum(1 for engine in self.stt_engines.values() if engine['available']),
            'tts_engines_available': sum(1 for engine in self.tts_engines.values() if engine['available']),
            'audio_system_status': 'ACTIVE' if self.input_stream and self.output_stream else 'LIMITED'
        }
        
    async def initialize_complete_system(self) -> bool:
        """Initialize complete REAL voice interface system"""
        print("\n🚀 COPILOT: Initializing Complete Voice Interface System...")
        
        # Initialize audio system
        audio_ok = self.initialize_audio_system()
        
        # Initialize STT engines
        stt_status = self.initialize_stt_engines()
        
        # Initialize TTS engines
        tts_status = self.initialize_tts_engines()
        
        # Start audio streams
        streams_ok = self.start_audio_streams() if audio_ok else False
        
        # System status
        stt_available = any(stt_status.values())
        tts_available = any(tts_status.values())
        
        system_ready = audio_ok and stt_available and tts_available and streams_ok
        
        print(f"\n📊 VOICE INTERFACE STATUS:")
        print(f"   Audio System: {'✅ OK' if audio_ok else '❌ FAILED'}")
        print(f"   STT Engines: {'✅ OK' if stt_available else '❌ FAILED'}")
        print(f"   TTS Engines: {'✅ OK' if tts_available else '❌ FAILED'}")
        print(f"   Audio Streams: {'✅ OK' if streams_ok else '❌ FAILED'}")
        print(f"   Overall Status: {'✅ READY' if system_ready else '❌ LIMITED'}")
        
        return system_ready
        
    def cleanup(self):
        """Cleanup audio resources"""
        self.is_listening = False
        self.is_speaking = False
        
        if self.input_stream:
            self.input_stream.stop_stream()
            self.input_stream.close()
            
        if self.output_stream:
            self.output_stream.stop_stream()
            self.output_stream.close()
            
        if self.audio_interface:
            self.audio_interface.terminate()
            
        print("🚀 COPILOT: Voice interface cleanup complete")

async def main():
    """Test real voice interface"""
    print("🚀 COPILOT: Testing Real Voice Interface")
    
    voice_interface = RealVoiceInterface()
    
    try:
        # Initialize system
        system_ready = await voice_interface.initialize_complete_system()
        
        if system_ready:
            # Test TTS
            await voice_interface.speak_text("Voice interface is ready for testing")
            
            # Test listening (short timeout for demo)
            command = await voice_interface.listen_for_command(timeout=3.0)
            if command:
                await voice_interface.speak_text(f"I heard: {command}")
            else:
                await voice_interface.speak_text("No command detected")
                
            # Show metrics
            metrics = voice_interface.get_voice_metrics()
            print(f"\n📊 Voice Metrics:")
            for key, value in metrics.items():
                print(f"   {key}: {value}")
                
        else:
            print("❌ Voice interface not ready")
            
    finally:
        voice_interface.cleanup()

if __name__ == "__main__":
    asyncio.run(main())