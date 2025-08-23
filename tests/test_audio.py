#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GEM OS - Audio System Tests
Comprehensive testing for audio functionality
"""

import pytest
import asyncio
import numpy as np
from unittest.mock import Mock, patch, AsyncMock
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.audio_system import AudioSystem

class TestAudioSystem:
    """Test cases for AudioSystem"""
    
    @pytest.fixture
    def audio_config(self):
        """Audio configuration for testing"""
        return {
            'device_index': None,
            'sample_rate': 16000,
            'channels': 1,
            'chunk_size': 1024,
            'noise_reduction': True,
            'auto_gain': True
        }
    
    @pytest.fixture
    def mock_logger(self):
        """Mock logger for testing"""
        return Mock()
    
    @pytest.fixture
    def audio_system(self, audio_config, mock_logger):
        """AudioSystem instance for testing"""
        return AudioSystem(config=audio_config, logger=mock_logger)
    
    def test_audio_system_initialization(self, audio_system):
        """Test AudioSystem initialization"""
        assert audio_system.sample_rate == 16000
        assert audio_system.channels == 1
        assert audio_system.chunk_size == 1024
        assert audio_system.noise_reduction == True
        assert audio_system.auto_gain == True
    
    @patch('sounddevice.query_devices')
    def test_get_audio_devices(self, mock_query_devices, audio_system):
        """Test audio device enumeration"""
        # Mock device list
        mock_devices = [
            {'name': 'Default', 'max_input_channels': 2, 'default_samplerate': 44100},
            {'name': 'USB Microphone', 'max_input_channels': 1, 'default_samplerate': 16000}
        ]
        mock_query_devices.return_value = mock_devices
        
        devices = audio_system.get_audio_devices()
        
        assert len(devices) == 2
        assert devices[0]['name'] == 'Default'
        assert devices[1]['name'] == 'USB Microphone'
    
    @patch('sounddevice.InputStream')
    @pytest.mark.asyncio
    async def test_initialize_audio_system(self, mock_input_stream, audio_system):
        """Test audio system initialization"""
        mock_stream = Mock()
        mock_input_stream.return_value = mock_stream
        
        await audio_system.initialize()
        
        assert audio_system.is_initialized == True
        mock_input_stream.assert_called_once()
    
    def test_generate_test_audio(self, audio_system):
        """Test test audio generation"""
        duration = 1.0  # 1 second
        frequency = 440  # A4 note
        
        audio_data = audio_system.generate_test_audio(duration, frequency)
        
        expected_samples = int(audio_system.sample_rate * duration)
        assert len(audio_data) == expected_samples
        assert isinstance(audio_data, np.ndarray)
        assert audio_data.dtype == np.float32
    
    def test_apply_noise_reduction(self, audio_system):
        """Test noise reduction functionality"""
        # Generate noisy audio
        clean_signal = np.sin(2 * np.pi * 440 * np.linspace(0, 1, 16000))
        noise = np.random.normal(0, 0.1, 16000)
        noisy_audio = clean_signal + noise
        
        # Apply noise reduction
        filtered_audio = audio_system.apply_noise_reduction(noisy_audio.astype(np.float32))
        
        assert isinstance(filtered_audio, np.ndarray)
        assert len(filtered_audio) == len(noisy_audio)
        # Noise reduction should reduce the noise level
        assert np.std(filtered_audio) <= np.std(noisy_audio)
    
    def test_apply_auto_gain(self, audio_system):
        """Test automatic gain control"""
        # Generate quiet audio
        quiet_audio = np.sin(2 * np.pi * 440 * np.linspace(0, 1, 16000)) * 0.1
        
        # Apply auto gain
        gained_audio = audio_system.apply_auto_gain(quiet_audio.astype(np.float32))
        
        assert isinstance(gained_audio, np.ndarray)
        assert len(gained_audio) == len(quiet_audio)
        # Auto gain should increase the amplitude
        assert np.max(np.abs(gained_audio)) > np.max(np.abs(quiet_audio))
    
    def test_detect_voice_activity(self, audio_system):
        """Test voice activity detection"""
        # Generate speech-like signal
        speech_signal = np.random.normal(0, 0.5, 16000).astype(np.float32)
        
        # Generate silence
        silence = np.zeros(16000, dtype=np.float32)
        
        # Test voice activity detection
        speech_vad = audio_system.detect_voice_activity(speech_signal)
        silence_vad = audio_system.detect_voice_activity(silence)
        
        assert isinstance(speech_vad, bool)
        assert isinstance(silence_vad, bool)
        assert speech_vad == True  # Should detect voice activity
        assert silence_vad == False  # Should not detect voice activity
    
    @pytest.mark.asyncio
    async def test_capture_audio_timeout(self, audio_system):
        """Test audio capture with timeout"""
        # Mock the audio capture to simulate timeout
        with patch.object(audio_system, '_capture_audio_chunk', return_value=None):
            audio_data = await audio_system.capture_audio(timeout=0.1)
            assert audio_data is None
    
    def test_audio_format_conversion(self, audio_system):
        """Test audio format conversions"""
        # Generate test audio
        test_audio = np.sin(2 * np.pi * 440 * np.linspace(0, 1, 16000))
        
        # Test float32 to int16 conversion
        int16_audio = audio_system.float32_to_int16(test_audio.astype(np.float32))
        assert int16_audio.dtype == np.int16
        assert len(int16_audio) == len(test_audio)
        
        # Test int16 to float32 conversion
        float32_audio = audio_system.int16_to_float32(int16_audio)
        assert float32_audio.dtype == np.float32
        assert len(float32_audio) == len(int16_audio)
    
    def test_audio_statistics(self, audio_system):
        """Test audio statistics calculation"""
        # Generate test audio with known properties
        test_audio = np.sin(2 * np.pi * 440 * np.linspace(0, 1, 16000)).astype(np.float32)
        
        stats = audio_system.get_audio_statistics(test_audio)
        
        assert 'rms_level' in stats
        assert 'peak_level' in stats
        assert 'zero_crossing_rate' in stats
        assert 'spectral_centroid' in stats
        
        assert isinstance(stats['rms_level'], float)
        assert isinstance(stats['peak_level'], float)
        assert isinstance(stats['zero_crossing_rate'], float)
        assert stats['peak_level'] >= stats['rms_level']
    
    @pytest.mark.asyncio
    async def test_audio_system_shutdown(self, audio_system):
        """Test audio system shutdown"""
        # Initialize first
        with patch('sounddevice.InputStream'):
            await audio_system.initialize()
        
        # Test shutdown
        audio_system.shutdown()
        
        assert audio_system.is_initialized == False
        assert audio_system.stream is None

@pytest.mark.integration
class TestAudioSystemIntegration:
    """Integration tests for AudioSystem (require actual hardware)"""
    
    @pytest.mark.skipif(not os.environ.get('RUN_INTEGRATION_TESTS'), 
                       reason="Integration tests disabled")
    @pytest.mark.asyncio
    async def test_real_audio_capture(self):
        """Test real audio capture (requires microphone)"""
        config = {
            'sample_rate': 16000,
            'channels': 1,
            'chunk_size': 1024
        }
        
        audio_system = AudioSystem(config=config)
        
        try:
            await audio_system.initialize()
            
            # Capture short audio sample
            audio_data = await audio_system.capture_audio(timeout=1.0)
            
            if audio_data is not None:
                assert isinstance(audio_data, np.ndarray)
                assert len(audio_data) > 0
                assert audio_data.dtype == np.float32
            
        finally:
            audio_system.shutdown()
    
    @pytest.mark.skipif(not os.environ.get('RUN_INTEGRATION_TESTS'), 
                       reason="Integration tests disabled")
    def test_audio_device_enumeration(self):
        """Test real audio device enumeration"""
        audio_system = AudioSystem()
        devices = audio_system.get_audio_devices()
        
        assert isinstance(devices, list)
        # Should have at least one device on most systems
        if len(devices) > 0:
            device = devices[0]
            assert 'name' in device
            assert 'max_input_channels' in device

if __name__ == '__main__':
    # Run tests
    pytest.main([__file__, '-v'])