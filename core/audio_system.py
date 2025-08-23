#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
💎 GEM OS - Advanced Audio System
Robust audio management with accessibility features
"""

import asyncio
import logging
import numpy as np
import sounddevice as sd
import soundfile as sf
import threading
import time
import webrtcvad
from pathlib import Path
from typing import Optional, Callable, List, Dict, Any
from dataclasses import dataclass

# Import state machine components (Copilot's suggestion + Gemini's design)
from .audio_states import AudioStateMachine, AudioState


@dataclass
class AudioDevice:
    """Audio device information."""
    index: int
    name: str
    channels: int
    sample_rate: float
    is_input: bool
    is_output: bool


class AudioProcessor:
    """Advanced audio processing utilities."""
    
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self.vad = webrtcvad.Vad(2)  # Aggressiveness level 0-3
    
    def apply_noise_reduction(self, audio_data: np.ndarray) -> np.ndarray:
        """Apply basic noise reduction."""
        # Simple spectral subtraction
        from scipy import signal
        
        # Apply a high-pass filter to remove low-frequency noise
        sos = signal.butter(5, 300, btype='high', fs=self.sample_rate, output='sos')
        filtered = signal.sosfilt(sos, audio_data)
        
        return filtered.astype(np.float32)
    
    def normalize_audio(self, audio_data: np.ndarray) -> np.ndarray:
        """Normalize audio levels."""
        max_val = np.max(np.abs(audio_data))
        if max_val > 0:
            return audio_data / max_val * 0.8
        return audio_data
    
    def detect_speech(self, audio_data: np.ndarray) -> bool:
        """Detect if audio contains speech using VAD."""
        try:
            # Convert to 16-bit PCM
            audio_16bit = (audio_data * 32767).astype(np.int16)
            
            # VAD requires specific sample rates
            if self.sample_rate not in [8000, 16000, 32000, 48000]:
                return self._energy_based_vad(audio_data)
            
            # Convert to bytes
            audio_bytes = audio_16bit.tobytes()
            
            # Check in chunks
            frame_duration = 30  # ms
            frame_size = int(self.sample_rate * frame_duration / 1000)
            
            speech_frames = 0
            total_frames = 0
            
            for i in range(0, len(audio_16bit), frame_size):
                frame = audio_16bit[i:i + frame_size]
                if len(frame) == frame_size:
                    frame_bytes = frame.tobytes()
                    if self.vad.is_speech(frame_bytes, self.sample_rate):
                        speech_frames += 1
                    total_frames += 1
            
            # Return True if more than 30% of frames contain speech
            return total_frames > 0 and (speech_frames / total_frames) > 0.3
        
        except Exception:
            # Fallback to energy-based detection
            return self._energy_based_vad(audio_data)
    
    def _energy_based_vad(self, audio_data: np.ndarray, threshold: float = 0.01) -> bool:
        """Fallback energy-based voice activity detection."""
        energy = np.mean(audio_data ** 2)
        return energy > threshold


class AudioSystem:
    """Advanced audio system with accessibility features."""
    
    def __init__(self, config, logger: Optional[logging.Logger] = None):
        self.config = config
        self.logger = logger or logging.getLogger("AudioSystem")
        
        # Audio settings
        self.sample_rate = config.sample_rate
        self.channels = config.channels
        self.chunk_size = config.chunk_size
        self.device_index = config.device_index
        
        # Processing
        self.processor = AudioProcessor(self.sample_rate)
        
        # State Machine (Copilot's suggestion + Gemini's design)
        self.state_machine = AudioStateMachine(self.logger)
        
        # Legacy state tracking (maintained for compatibility)
        self.is_listening = False
        self.is_recording = False
        self.audio_buffer = []
        self.silence_start = None
        
        # Callbacks
        self.wake_word_callback: Optional[Callable] = None
        self.speech_callback: Optional[Callable] = None
        
        # Threading
        self.listen_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
        # Devices
        self.input_device: Optional[AudioDevice] = None
        self.output_device: Optional[AudioDevice] = None
        
        # Wake word detection
        self.wake_word_detector = None
    
    async def initialize(self):
        """Initialize the audio system."""
        self.logger.info("Initializing audio system...")
        
        # Discover audio devices
        await self._discover_devices()
        
        # Setup devices
        await self._setup_devices()
        
        # Initialize wake word detection
        await self._initialize_wake_word_detection()
        
        self.logger.info("Audio system initialized successfully")
    
    async def _discover_devices(self):
        """Discover available audio devices."""
        self.logger.info("Discovering audio devices...")
        
        devices = sd.query_devices()
        self.available_devices = []
        
        for i, device in enumerate(devices):
            audio_device = AudioDevice(
                index=i,
                name=device['name'],
                channels=device['max_input_channels'],
                sample_rate=device['default_samplerate'],
                is_input=device['max_input_channels'] > 0,
                is_output=device['max_output_channels'] > 0
            )
            self.available_devices.append(audio_device)
            
            self.logger.debug(f"Device {i}: {device['name']} "
                            f"(In: {device['max_input_channels']}, "
                            f"Out: {device['max_output_channels']})")
    
    async def _setup_devices(self):
        """Setup input and output devices."""
        # Auto-select devices if not specified
        if self.config.device_index is None:
            # Use default input device
            default_input = sd.query_devices(kind='input')
            self.input_device = AudioDevice(
                index=sd.default.device[0] if sd.default.device[0] is not None else 0,
                name=default_input['name'],
                channels=default_input['max_input_channels'],
                sample_rate=default_input['default_samplerate'],
                is_input=True,
                is_output=False
            )
        else:
            self.input_device = self.available_devices[self.config.device_index]
        
        self.logger.info(f"Using input device: {self.input_device.name}")
    
    async def _initialize_wake_word_detection(self):
        """Initialize wake word detection."""
        try:
            # Try to use Porcupine for wake word detection
            import pvporcupine
            
            # Use built-in wake words or custom ones
            keywords = ["hey google"]  # Fallback, will be replaced with custom
            
            self.wake_word_detector = pvporcupine.create(
                keywords=keywords,
                sensitivities=[0.5] * len(keywords)
            )
            
            self.logger.info("Wake word detection initialized with Porcupine")
        
        except ImportError:
            self.logger.warning("Porcupine not available, using simple keyword detection")
            self.wake_word_detector = None
        
        except Exception as e:
            self.logger.error(f"Error initializing wake word detection: {e}")
            self.wake_word_detector = None
    
    def set_wake_word_callback(self, callback: Callable):
        """Set callback for wake word detection."""
        self.wake_word_callback = callback
    
    def set_speech_callback(self, callback: Callable):
        """Set callback for speech detection."""
        self.speech_callback = callback
    
    def start_listening(self):
        """Start listening for audio with state machine management."""
        # Check if we can transition to listening state
        if not self.state_machine.can_transition_to(AudioState.LISTENING):
            self.logger.warning(f"Cannot start listening from current state: {self.state_machine.get_current_state().name}")
            return
        
        # Transition to listening state
        if not self.state_machine.transition_to(AudioState.LISTENING, {'action': 'start_listening'}):
            self.logger.error("Failed to transition to listening state")
            return
        
        self.is_listening = True
        self.stop_event.clear()
        
        self.listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.listen_thread.start()
        
        self.logger.info("Started listening for audio with state machine management")
    
    def stop_listening(self):
        """Stop listening for audio with state machine management."""
        if not self.is_listening:
            return
        
        # Transition to idle state
        self.state_machine.transition_to(AudioState.IDLE, {'action': 'stop_listening'})
        
        self.is_listening = False
        self.stop_event.set()
        
        if self.listen_thread:
            self.listen_thread.join(timeout=2.0)
        
        self.logger.info("Stopped listening for audio with state machine management")
    
    def _listen_loop(self):
        """Main audio listening loop."""
        try:
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype=np.float32,
                blocksize=self.chunk_size,
                device=self.input_device.index if self.input_device else None,
                callback=self._audio_callback
            ):
                while not self.stop_event.wait(0.1):
                    pass
        
        except Exception as e:
            self.logger.error(f"Error in listen loop: {e}")
    
    def _audio_callback(self, indata, frames, time, status):
        """Audio input callback."""
        if status:
            self.logger.warning(f"Audio callback status: {status}")
        
        # Convert to numpy array
        audio_chunk = indata[:, 0] if self.channels == 1 else indata
        
        # Apply audio processing
        if self.config.noise_reduction:
            audio_chunk = self.processor.apply_noise_reduction(audio_chunk)
        
        audio_chunk = self.processor.normalize_audio(audio_chunk)
        
        # Check for wake word
        if not self.is_recording:
            self._check_wake_word(audio_chunk)
        
        # Handle speech recording
        if self.is_recording:
            self._handle_speech_recording(audio_chunk)
    
    def _check_wake_word(self, audio_chunk: np.ndarray):
        """Check for wake word in audio chunk."""
        if self.wake_word_detector:
            # Use Porcupine for wake word detection
            try:
                # Convert to 16-bit PCM
                pcm = (audio_chunk * 32767).astype(np.int16)
                keyword_index = self.wake_word_detector.process(pcm)
                
                if keyword_index >= 0:
                    self._on_wake_word_detected("wake_word")
            
            except Exception as e:
                self.logger.error(f"Wake word detection error: {e}")
        
        else:
            # Simple energy-based detection as fallback
            if self.processor.detect_speech(audio_chunk):
                energy = np.mean(audio_chunk ** 2)
                if energy > self.config.volume_threshold:
                    self._on_wake_word_detected("speech_detected")
    
    def _handle_speech_recording(self, audio_chunk: np.ndarray):
        """Handle speech recording after wake word."""
        # Check if there's speech in this chunk
        has_speech = self.processor.detect_speech(audio_chunk)
        
        if has_speech:
            self.audio_buffer.append(audio_chunk)
            self.silence_start = None
        else:
            # Track silence
            if self.silence_start is None:
                self.silence_start = time.time()
            
            # If silence exceeds threshold, stop recording
            if time.time() - self.silence_start > self.config.silence_timeout:
                self._finish_recording()
            else:
                # Still add to buffer during short silence
                self.audio_buffer.append(audio_chunk)
    
    def _on_wake_word_detected(self, keyword: str):
        """Handle wake word detection with state machine."""
        self.logger.info(f"Wake word detected: {keyword}")
        
        # Transition to processing state
        if self.state_machine.transition_to(AudioState.PROCESSING, {
            'wake_word': keyword,
            'action': 'wake_word_detected'
        }):
            # Start recording speech
            self.is_recording = True
            self.audio_buffer = []
            self.silence_start = None
            
            # Call callback if set
            if self.wake_word_callback:
                asyncio.create_task(self.wake_word_callback(keyword))
        else:
            self.logger.warning("Could not transition to processing state for wake word")
    
    def _finish_recording(self):
        """Finish speech recording and process with state machine."""
        if not self.audio_buffer:
            self.is_recording = False
            # Return to listening state
            self.state_machine.transition_to(AudioState.LISTENING, {'action': 'recording_finished_empty'})
            return
        
        # Combine audio chunks
        audio_data = np.concatenate(self.audio_buffer)
        
        # Convert to bytes for STT
        audio_bytes = (audio_data * 32767).astype(np.int16).tobytes()
        
        duration = len(audio_data) / self.sample_rate
        self.logger.info(f"Recorded {len(audio_data)} samples ({duration:.2f}s)")
        
        # Transition to speaking state (assuming TTS will follow)
        self.state_machine.transition_to(AudioState.SPEAKING, {
            'action': 'processing_speech',
            'audio_duration': duration,
            'audio_samples': len(audio_data)
        })
        
        # Reset recording state
        self.is_recording = False
        self.audio_buffer = []
        
        # Call speech callback
        if self.speech_callback:
            asyncio.create_task(self.speech_callback(audio_bytes))
            
        # After processing, return to listening
        # This will be called after TTS completes
        asyncio.create_task(self._return_to_listening_after_delay(2.0))
    
    async def play_audio_file(self, file_path: Path):
        """Play an audio file."""
        try:
            data, sample_rate = sf.read(file_path)
            sd.play(data, sample_rate)
            sd.wait()  # Wait until playback is finished
        
        except Exception as e:
            self.logger.error(f"Error playing audio file {file_path}: {e}")
    
    async def record_audio(self, duration: float, output_path: Optional[Path] = None) -> Optional[np.ndarray]:
        """Record audio for a specific duration."""
        try:
            self.logger.info(f"Recording audio for {duration} seconds...")
            
            recording = sd.rec(
                int(duration * self.sample_rate),
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype=np.float32
            )
            sd.wait()  # Wait until recording is finished
            
            if output_path:
                sf.write(output_path, recording, self.sample_rate)
                self.logger.info(f"Audio saved to {output_path}")
            
            return recording
        
        except Exception as e:
            self.logger.error(f"Error recording audio: {e}")
            return None
    
    async def test_audio(self):
        """Test audio input and output."""
        self.logger.info("Testing audio system...")
        
        # Test input
        try:
            test_duration = 2.0
            self.logger.info(f"Recording test audio for {test_duration} seconds...")
            
            recording = await self.record_audio(test_duration)
            
            if recording is not None:
                # Analyze recording
                max_amplitude = np.max(np.abs(recording))
                rms = np.sqrt(np.mean(recording ** 2))
                
                self.logger.info(f"Recording stats - Max: {max_amplitude:.4f}, RMS: {rms:.4f}")
                
                if max_amplitude > 0.01:
                    self.logger.info("✅ Audio input test passed")
                else:
                    self.logger.warning("⚠️ Audio input seems very quiet")
            else:
                self.logger.error("❌ Audio input test failed")
        
        except Exception as e:
            self.logger.error(f"Audio test error: {e}")
    
    def get_audio_devices(self) -> List[AudioDevice]:
        """Get list of available audio devices."""
        return self.available_devices
    
    def set_input_device(self, device_index: int):
        """Set input device by index."""
        if 0 <= device_index < len(self.available_devices):
            device = self.available_devices[device_index]
            if device.is_input:
                self.input_device = device
                self.config.device_index = device_index
                self.logger.info(f"Input device set to: {device.name}")
            else:
                self.logger.error("Selected device is not an input device")
        else:
            self.logger.error("Invalid device index")
    
    async def _return_to_listening_after_delay(self, delay: float):
        """Return to listening state after a delay."""
        await asyncio.sleep(delay)
        if self.state_machine.can_transition_to(AudioState.LISTENING):
            self.state_machine.transition_to(AudioState.LISTENING, {'action': 'auto_return_to_listening'})
    
    def get_audio_state(self) -> Dict[str, Any]:
        """Get current audio system state information."""
        return {
            'state_machine': self.state_machine.get_state_info(),
            'is_listening': self.is_listening,
            'is_recording': self.is_recording,
            'buffer_size': len(self.audio_buffer),
            'devices': {
                'input': self.input_device.name if self.input_device else None,
                'output': self.output_device.name if self.output_device else None
            }
        }
    
    def force_state_reset(self):
        """Force reset audio state machine to idle (emergency function)."""
        self.logger.warning("Forcing audio state machine reset to idle")
        self.state_machine.reset_to_idle()
        self.is_recording = False
        self.audio_buffer = []
    
    def shutdown(self):
        """Shutdown the audio system with state machine management."""
        self.logger.info("Shutting down audio system...")
        
        # Transition to shutdown state
        self.state_machine.transition_to(AudioState.SHUTDOWN, {'action': 'system_shutdown'})
        
        self.stop_listening()
        
        if self.wake_word_detector:
            try:
                self.wake_word_detector.delete()
            except:
                pass
        
        self.logger.info("Audio system shutdown complete with state machine management")