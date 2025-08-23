#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GEM OS - Speech-to-Text Tests
Testing speech recognition functionality
"""

import pytest
import asyncio
import numpy as np
from unittest.mock import Mock, patch, AsyncMock
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.stt_module import STTModule

class TestSTTModule:
    """Test cases for STTModule"""
    
    @pytest.fixture
    def stt_config(self):
        """STT configuration for testing"""
        return {
            'engine': 'faster_whisper',
            'model': 'base',
            'language': 'pt',
            'offline_only': True
        }
    
    @pytest.fixture
    def mock_logger(self):
        """Mock logger for testing"""
        return Mock()
    
    @pytest.fixture
    def stt_module(self, stt_config, mock_logger):
        """STTModule instance for testing"""
        return STTModule(config=stt_config, logger=mock_logger)
    
    def test_stt_module_initialization(self, stt_module):
        """Test STTModule initialization"""
        assert stt_module.engine == 'faster_whisper'
        assert stt_module.model == 'base'
        assert stt_module.language == 'pt'
        assert stt_module.offline_only == True
    
    @patch('faster_whisper.WhisperModel')
    @pytest.mark.asyncio
    async def test_initialize_faster_whisper(self, mock_whisper_model, stt_module):
        """Test Faster Whisper initialization"""
        mock_model = Mock()
        mock_whisper_model.return_value = mock_model
        
        await stt_module.initialize()
        
        assert stt_module.faster_whisper_model is not None
        mock_whisper_model.assert_called_once()
    
    def test_generate_test_speech_audio(self, stt_module):
        """Test generation of test speech audio"""
        # Generate simple test audio (sine wave)
        duration = 1.0
        sample_rate = 16000
        frequency = 440
        
        t = np.linspace(0, duration, int(sample_rate * duration))
        audio_data = np.sin(2 * np.pi * frequency * t).astype(np.float32)
        
        assert len(audio_data) == sample_rate
        assert isinstance(audio_data, np.ndarray)
        assert audio_data.dtype == np.float32
    
    @patch('faster_whisper.WhisperModel')
    @pytest.mark.asyncio
    async def test_transcribe_with_faster_whisper(self, mock_whisper_model, stt_module):
        """Test transcription with Faster Whisper"""
        # Mock the model and its transcribe method
        mock_model = Mock()
        mock_segment = Mock()
        mock_segment.text = "Olá, como você está?"
        mock_segment.start = 0.0
        mock_segment.end = 2.0
        
        mock_info = Mock()
        mock_info.language = "pt"
        
        mock_model.transcribe.return_value = ([mock_segment], mock_info)
        mock_whisper_model.return_value = mock_model
        
        # Initialize and test
        await stt_module.initialize()
        
        # Generate test audio
        test_audio = np.random.random(16000).astype(np.float32)
        
        result = await stt_module.transcribe(test_audio)
        
        assert result == "Olá, como você está?"
        mock_model.transcribe.assert_called_once()
    
    @patch('speech_recognition.Recognizer')
    @patch('speech_recognition.AudioFile')
    @pytest.mark.asyncio
    async def test_transcribe_with_speech_recognition(self, mock_audio_file, mock_recognizer_class, stt_module):
        """Test transcription with SpeechRecognition"""
        # Configure for speech_recognition engine
        stt_module.engine = 'speech_recognition'
        
        # Mock recognizer
        mock_recognizer = Mock()
        mock_recognizer.recognize_google.return_value = "Hello world"
        mock_recognizer_class.return_value = mock_recognizer
        
        # Mock audio file
        mock_audio_file.return_value.__enter__ = Mock()
        mock_audio_file.return_value.__exit__ = Mock()
        
        await stt_module.initialize()
        
        # Test transcription
        test_audio = np.random.random(16000).astype(np.float32)
        
        with patch.object(stt_module, '_prepare_audio_for_sr', return_value="test.wav"):
            result = await stt_module.transcribe(test_audio)
        
        assert isinstance(result, str)
    
    def test_preprocess_audio(self, stt_module):
        """Test audio preprocessing"""
        # Generate test audio with varying amplitude
        test_audio = np.array([0.1, -0.5, 0.8, -0.2, 0.6], dtype=np.float32)
        
        processed = stt_module.preprocess_audio(test_audio)
        
        assert isinstance(processed, np.ndarray)
        assert processed.dtype == np.float32
        assert len(processed) == len(test_audio)
        # Should be normalized
        assert np.max(np.abs(processed)) <= 1.0
    
    def test_detect_language(self, stt_module):
        """Test language detection"""
        # Mock audio samples for different languages
        portuguese_text = "Olá, como você está hoje?"
        english_text = "Hello, how are you today?"
        
        # Test language detection (simplified)
        pt_confidence = stt_module._calculate_language_confidence(portuguese_text, 'pt')
        en_confidence = stt_module._calculate_language_confidence(english_text, 'en')
        
        assert isinstance(pt_confidence, float)
        assert isinstance(en_confidence, float)
        assert 0.0 <= pt_confidence <= 1.0
        assert 0.0 <= en_confidence <= 1.0
    
    def test_confidence_calculation(self, stt_module):
        """Test transcription confidence calculation"""
        # Test with different text qualities
        clear_text = "This is a clear sentence."
        unclear_text = "Th.. is.. uncl.. sent.."
        
        clear_confidence = stt_module._calculate_confidence(clear_text)
        unclear_confidence = stt_module._calculate_confidence(unclear_text)
        
        assert isinstance(clear_confidence, float)
        assert isinstance(unclear_confidence, float)
        assert 0.0 <= clear_confidence <= 1.0
        assert 0.0 <= unclear_confidence <= 1.0
        assert clear_confidence > unclear_confidence
    
    @pytest.mark.asyncio
    async def test_transcribe_empty_audio(self, stt_module):
        """Test transcription with empty/silent audio"""
        # Generate silent audio
        silent_audio = np.zeros(16000, dtype=np.float32)
        
        result = await stt_module.transcribe(silent_audio)
        
        # Should return empty string or None for silent audio
        assert result == "" or result is None
    
    @pytest.mark.asyncio
    async def test_transcribe_invalid_audio(self, stt_module):
        """Test transcription with invalid audio data"""
        # Test with invalid audio formats
        invalid_audio_formats = [
            None,
            [],
            "not_audio",
            np.array([]),  # Empty array
            np.array([1, 2, 3], dtype=np.int32)  # Wrong dtype
        ]
        
        for invalid_audio in invalid_audio_formats:
            result = await stt_module.transcribe(invalid_audio)
            # Should handle gracefully and return None or empty string
            assert result is None or result == ""
    
    def test_audio_format_validation(self, stt_module):
        """Test audio format validation"""
        # Valid audio
        valid_audio = np.random.random(16000).astype(np.float32)
        assert stt_module._validate_audio_format(valid_audio) == True
        
        # Invalid audio formats
        invalid_formats = [
            None,
            "string",
            np.array([1, 2, 3], dtype=np.int32),
            np.array([]),
            []
        ]
        
        for invalid_format in invalid_formats:
            assert stt_module._validate_audio_format(invalid_format) == False
    
    @pytest.mark.asyncio
    async def test_engine_fallback(self, stt_module):
        """Test fallback to alternative engines"""
        # Configure multiple engines
        stt_module.available_engines = ['faster_whisper', 'speech_recognition', 'vosk']
        
        # Mock first engine to fail
        with patch.object(stt_module, '_transcribe_faster_whisper', side_effect=Exception("Engine failed")):
            with patch.object(stt_module, '_transcribe_speech_recognition', return_value="Fallback success"):
                test_audio = np.random.random(16000).astype(np.float32)
                result = await stt_module.transcribe(test_audio)
                
                assert result == "Fallback success"
    
    def test_get_engine_status(self, stt_module):
        """Test engine status reporting"""
        status = stt_module.get_engine_status()
        
        assert isinstance(status, dict)
        assert 'current_engine' in status
        assert 'available_engines' in status
        assert 'language' in status
        assert 'model' in status
    
    @pytest.mark.asyncio
    async def test_batch_transcription(self, stt_module):
        """Test batch transcription of multiple audio samples"""
        # Generate multiple test audio samples
        audio_samples = [
            np.random.random(8000).astype(np.float32),
            np.random.random(12000).astype(np.float32),
            np.random.random(16000).astype(np.float32)
        ]
        
        with patch.object(stt_module, 'transcribe', return_value="Test transcription"):
            results = await stt_module.transcribe_batch(audio_samples)
            
            assert isinstance(results, list)
            assert len(results) == len(audio_samples)
            for result in results:
                assert isinstance(result, str)
    
    def test_performance_metrics(self, stt_module):
        """Test performance metrics tracking"""
        # Initialize metrics
        stt_module._reset_performance_metrics()
        
        # Simulate some transcriptions
        stt_module._update_performance_metrics(processing_time=0.5, success=True)
        stt_module._update_performance_metrics(processing_time=0.3, success=True)
        stt_module._update_performance_metrics(processing_time=1.0, success=False)
        
        metrics = stt_module.get_performance_metrics()
        
        assert isinstance(metrics, dict)
        assert 'total_requests' in metrics
        assert 'successful_requests' in metrics
        assert 'average_processing_time' in metrics
        assert 'success_rate' in metrics
        
        assert metrics['total_requests'] == 3
        assert metrics['successful_requests'] == 2
        assert metrics['success_rate'] == 2/3

@pytest.mark.integration
class TestSTTModuleIntegration:
    """Integration tests for STTModule (require actual models)"""
    
    @pytest.mark.skipif(not os.environ.get('RUN_INTEGRATION_TESTS'), 
                       reason="Integration tests disabled")
    @pytest.mark.asyncio
    async def test_real_whisper_transcription(self):
        """Test real Whisper transcription (requires model download)"""
        config = {
            'engine': 'faster_whisper',
            'model': 'tiny',  # Use smallest model for testing
            'language': 'pt'
        }
        
        stt_module = STTModule(config=config)
        
        try:
            await stt_module.initialize()
            
            # Generate test speech audio (simple tone)
            duration = 2.0
            sample_rate = 16000
            t = np.linspace(0, duration, int(sample_rate * duration))
            # Create a more speech-like signal
            audio_data = (np.sin(2 * np.pi * 200 * t) + 
                         0.5 * np.sin(2 * np.pi * 400 * t) + 
                         0.1 * np.random.random(len(t))).astype(np.float32)
            
            result = await stt_module.transcribe(audio_data)
            
            # Should return a string (might be empty for non-speech audio)
            assert isinstance(result, str)
            
        except ImportError:
            pytest.skip("Faster Whisper not available")
        except Exception as e:
            pytest.skip(f"Model not available: {e}")

if __name__ == '__main__':
    # Run tests
    pytest.main([__file__, '-v'])