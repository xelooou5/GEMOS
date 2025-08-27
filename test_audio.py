#!/usr/bin/env python3
"""
🧪 GEM OS - Audio System Test
Tests microphone, speakers, and voice processing
"""

import pyaudio
import wave
import time
import pyttsx3

def test_audio_devices():
    """Test available audio devices"""
    print("🎤 Testing audio devices...")
    
    try:
        p = pyaudio.PyAudio()
        
        print(f"📊 Found {p.get_device_count()} audio devices:")
        
        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            print(f"   {i}: {info['name']} - {info['maxInputChannels']}in/{info['maxOutputChannels']}out")
            
        p.terminate()
        return True
        
    except Exception as e:
        print(f"❌ Audio device test failed: {e}")
        return False

def test_microphone():
    """Test microphone recording"""
    print("🎤 Testing microphone...")
    
    try:
        p = pyaudio.PyAudio()
        
        # Record for 2 seconds
        stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=1024
        )
        
        print("🔴 Recording for 2 seconds...")
        frames = []
        for _ in range(0, int(16000 / 1024 * 2)):
            data = stream.read(1024)
            frames.append(data)
            
        stream.stop_stream()
        stream.close()
        p.terminate()
        
        print("✅ Microphone recording successful")
        return True
        
    except Exception as e:
        print(f"❌ Microphone test failed: {e}")
        return False

def test_speakers():
    """Test text-to-speech output"""
    print("🔊 Testing speakers with TTS...")
    
    try:
        engine = pyttsx3.init()
        engine.setProperty('rate', 150)
        engine.say("GEM OS audio system test successful")
        engine.runAndWait()
        
        print("✅ Speaker/TTS test successful")
        return True
        
    except Exception as e:
        print(f"❌ Speaker/TTS test failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 GEM OS - Audio System Test")
    print("=" * 40)
    
    devices_ok = test_audio_devices()
    mic_ok = test_microphone()
    speakers_ok = test_speakers()
    
    print("\n📊 Test Results:")
    print(f"   Audio Devices: {'✅' if devices_ok else '❌'}")
    print(f"   Microphone: {'✅' if mic_ok else '❌'}")
    print(f"   Speakers/TTS: {'✅' if speakers_ok else '❌'}")
    
    if devices_ok and mic_ok and speakers_ok:
        print("\n🎉 Audio system fully functional!")
    else:
        print("\n⚠️ Audio system needs attention")
