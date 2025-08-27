#!/usr/bin/env python3
"""
🔥 ONE HOUR INTEGRATION TEST - FIX ALL PILLARS
Complete system test and fix in one hour
"""

import subprocess
import asyncio
from datetime import datetime

class OneHourIntegrationTest:
    def __init__(self):
        self.start_time = datetime.now()
        
    async def run_one_hour_test(self):
        """🔥 Complete integration test in one hour"""
        print("🔥 STARTING ONE HOUR INTEGRATION TEST")
        print(f"⏰ Start Time: {self.start_time.strftime('%H:%M:%S')}")
        
        # Step 1: Install dependencies (5 minutes)
        await self.install_dependencies()
        
        # Step 2: Test LISTEN pillar (10 minutes)
        await self.test_listen_pillar()
        
        # Step 3: Test TALK pillar (10 minutes)
        await self.test_talk_pillar()
        
        # Step 4: Test ACTION pillar (10 minutes)
        await self.test_action_pillar()
        
        # Step 5: Test MEMORY pillar (10 minutes)
        await self.test_memory_pillar()
        
        # Step 6: Test complete integration (15 minutes)
        await self.test_complete_integration()
        
        print("✅ ONE HOUR TEST COMPLETE!")
        
    async def install_dependencies(self):
        """Install missing dependencies"""
        print("📦 INSTALLING DEPENDENCIES...")
        
        deps = [
            "pip install --break-system-packages faster-whisper",
            "pip install --break-system-packages edge-tts",
            "pip install --break-system-packages vosk",
            "pip install --break-system-packages pyttsx3",
            "pip install --break-system-packages pyaudio"
        ]
        
        for dep in deps:
            try:
                subprocess.run(dep.split(), timeout=60)
                print(f"✅ {dep}")
            except:
                print(f"❌ {dep}")
                
    async def test_listen_pillar(self):
        """Test LISTEN pillar"""
        print("🎤 TESTING LISTEN PILLAR...")
        subprocess.run(["python3", "copilot_listen_fix.py"])
        
    async def test_talk_pillar(self):
        """Test TALK pillar"""
        print("🗣️ TESTING TALK PILLAR...")
        subprocess.run(["python3", "gemini_talk_fix.py"])
        
    async def test_action_pillar(self):
        """Test ACTION pillar"""
        print("🎯 TESTING ACTION PILLAR...")
        subprocess.run(["python3", "cursor_action_fix.py"])
        
    async def test_memory_pillar(self):
        """Test MEMORY pillar"""
        print("🧠 TESTING MEMORY PILLAR...")
        subprocess.run(["python3", "tabnine_memory_fix.py"])
        
    async def test_complete_integration(self):
        """Test complete system integration"""
        print("🔥 TESTING COMPLETE INTEGRATION...")
        subprocess.run(["python3", "voice_system_complete.py"], timeout=30)

if __name__ == "__main__":
    test = OneHourIntegrationTest()
    asyncio.run(test.run_one_hour_test())