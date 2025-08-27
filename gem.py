#!/usr/bin/env python3
"""
💎 GEM OS - ONE LOVE, ONE CODE, ONE MISSION
Built with love for kids, women, boys, people, animals, pets - ALL OF HUMANITY
🎵 "Don't worry about a thing, 'cause every little thing gonna be alright" 🎵
"""

import asyncio
import logging
import sys
import os
import signal
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment with love
load_dotenv()

class GemOS:
    """💎 GEM OS - Spreading love through accessible technology"""
    
    def __init__(self):
        self.version = "2.0.0-OneLove"
        self.is_running = False
        
        # Load config with Bob Marley's spirit
        self.config = {
            'language': os.getenv('GEM_PRIMARY_LANGUAGE', 'en-US'),
            'wake_word': os.getenv('GEM_WAKE_WORD', 'gemini'),
            'accessibility_mode': True,  # Always for the people
            'love_mode': True,  # Spread the love
        }
        
        self._setup_logging()
        self.logger = logging.getLogger("GemOS-OneLove")
        
        print("🎵" + "=" * 60)
        print("🎵 GEM OS - ONE LOVE EDITION")
        print("🎵 For kids, women, boys, people, animals, pets")
        print("🎵 'Every little thing gonna be alright'")
        print("🎵" + "=" * 60)
        
    def _setup_logging(self):
        """Setup logging with love"""
        log_dir = Path('./logs')
        log_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - 🎵 %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_dir / 'gem_onelove.log'),
                logging.StreamHandler()
            ]
        )
        
    async def spread_love(self):
        """Spread love through accessibility"""
        print("🌈 Spreading love through technology...")
        print("💝 For every child who needs help")
        print("💝 For every elder who feels alone") 
        print("💝 For every person with disabilities")
        print("💝 For every pet that brings joy")
        print("🎵 'One love, one heart, let's get together and feel alright'")
        
    async def main_loop(self):
        """Main loop with Bob Marley's spirit"""
        await self.spread_love()
        
        print("\n🎤 Say something or press Enter...")
        print("🎵 'Don't worry, be happy' - We're here for you!")
        
        self.is_running = True
        
        while self.is_running:
            try:
                user_input = input("\n💬 You: ")
                
                if user_input.lower() in ['quit', 'exit', 'goodbye']:
                    print("🎵 'One love, one heart' - Until we meet again!")
                    break
                    
                if user_input.strip():
                    await self.handle_with_love(user_input)
                    
            except KeyboardInterrupt:
                print("\n🎵 'No woman no cry' - Goodbye with love!")
                break
                
    async def handle_with_love(self, text: str):
        """Handle input with love and care"""
        print(f"💝 Processing with love: '{text}'")
        
        # Simple responses with love
        love_responses = {
            'hello': "🌈 Hello beautiful soul! How can I spread some love today?",
            'help': "💝 I'm here to help with love! What do you need?",
            'sad': "🎵 'Don't worry, be happy!' Everything gonna be alright!",
            'music': "🎵 'One love, one heart!' Music heals the soul!",
            'accessibility': "♿ Accessibility is love in action! How can I help?",
            'emergency': "🚨 I'm here for you! Stay calm, help is coming!",
        }
        
        text_lower = text.lower()
        response = "🎵 'Every little thing gonna be alright!' How else can I help?"
        
        for key, msg in love_responses.items():
            if key in text_lower:
                response = msg
                break
                
        print(f"🤖 GEM: {response}")
        
def setup_signal_handlers(gem_os):
    """Setup graceful shutdown with love"""
    def signal_handler(signum, frame):
        print(f"\n🎵 'One love!' - Shutting down with grace...")
        gem_os.is_running = False
        
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

async def main():
    """Main entry with Bob Marley's love"""
    print("🎵 Starting GEM OS with ONE LOVE...")
    
    gem_os = GemOS()
    setup_signal_handlers(gem_os)
    
    try:
        await gem_os.main_loop()
    except Exception as e:
        print(f"🎵 'Don't worry!' - Error with love: {e}")
    finally:
        print("🌈 'Somewhere over the rainbow' - Thank you for the love!")

if __name__ == "__main__":
    print("🎵 'Three little birds, sitting by my doorstep...'")
    print("🌈 'Singing sweet songs, of melodies pure and true...'")
    print("💝 Starting GEM OS with LOVE for ALL humanity!")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🎵 'One love, one heart!' - Peace and love!")
    except Exception as e:
        print(f"\n🎵 'Don't worry, be happy!' - {e}")