#!/bin/bash
# 🔧 GEM OS - AUDIO SYSTEM FIX SCRIPT
# Fixes ALSA, PyAudio, and audio permissions issues

echo "🔧 GEM OS - FIXING AUDIO SYSTEM..."
echo "🎯 Resolving ALSA, PyAudio, and permission issues"

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "❌ Don't run as root! Run as regular user."
    exit 1
fi

# 1. Install audio dependencies
echo "📦 Installing audio dependencies..."
sudo apt update
sudo apt install -y \
    alsa-utils \
    pulseaudio \
    pulseaudio-utils \
    libasound2-dev \
    portaudio19-dev \
    python3-pyaudio \
    pavucontrol \
    alsa-base \
    alsa-tools

# 2. Add user to audio group
echo "👤 Adding user to audio group..."
sudo usermod -a -G audio $USER

# 3. Fix ALSA configuration
echo "🔧 Fixing ALSA configuration..."
sudo tee /etc/asound.conf > /dev/null << 'EOF'
# GEM OS - ALSA Configuration
pcm.!default {
    type pulse
}
ctl.!default {
    type pulse
}

pcm.pulse {
    type pulse
}
ctl.pulse {
    type pulse
}
EOF

# 4. Create user ALSA config
echo "👤 Creating user ALSA config..."
mkdir -p ~/.config/alsa
tee ~/.config/alsa/asoundrc > /dev/null << 'EOF'
# GEM OS - User ALSA Configuration
defaults.pcm.card 0
defaults.ctl.card 0
EOF

# 5. Fix PulseAudio configuration
echo "🔊 Configuring PulseAudio..."
mkdir -p ~/.config/pulse
tee ~/.config/pulse/default.pa > /dev/null << 'EOF'
# GEM OS - PulseAudio Configuration
.include /etc/pulse/default.pa

# Load audio modules
load-module module-alsa-sink device=hw:0,0
load-module module-alsa-source device=hw:0,0

# Set default sink and source
set-default-sink alsa_output.hw_0_0
set-default-source alsa_input.hw_0_0
EOF

# 6. Install Python audio libraries
echo "🐍 Installing Python audio libraries..."
pip3 install --user \
    pyaudio \
    pyttsx3 \
    SpeechRecognition \
    sounddevice \
    wave

# 7. Test audio system
echo "🧪 Testing audio system..."

# Test ALSA
echo "🔊 Testing ALSA..."
if aplay -l > /dev/null 2>&1; then
    echo "✅ ALSA working"
else
    echo "❌ ALSA issues detected"
fi

# Test PulseAudio
echo "🔊 Testing PulseAudio..."
if pulseaudio --check; then
    echo "✅ PulseAudio running"
else
    echo "🔄 Starting PulseAudio..."
    pulseaudio --start
fi

# Test PyAudio
echo "🐍 Testing PyAudio..."
python3 -c "
try:
    import pyaudio
    p = pyaudio.PyAudio()
    devices = p.get_device_count()
    print(f'✅ PyAudio working - {devices} devices found')
    p.terminate()
except Exception as e:
    print(f'❌ PyAudio error: {e}')
"

# 8. Create audio test script
echo "📝 Creating audio test script..."
tee test_audio.py > /dev/null << 'EOF'
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
EOF

chmod +x test_audio.py

# 9. Final instructions
echo ""
echo "🎯 AUDIO SYSTEM FIX COMPLETE!"
echo ""
echo "📋 NEXT STEPS:"
echo "1. 🔄 Restart your terminal (or logout/login)"
echo "2. 🧪 Run: python3 test_audio.py"
echo "3. 🚀 If tests pass, run: python3 gem_unified_system.py"
echo ""
echo "🔧 If issues persist:"
echo "   - Check audio cables/connections"
echo "   - Restart computer"
echo "   - Run: pulseaudio --kill && pulseaudio --start"
echo ""
echo "✅ Audio system should now work with GEM OS!"