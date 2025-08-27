#!/usr/bin/env python3
"""
💎 GEM OS - UNIFIED SYSTEM (CLEAN SLATE APPROACH)
All AI agents consolidated into ONE working system
SACRED RULE: This is the ONE main file - never rename, only enhance
"""

import asyncio
import os
import sys
import json
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class GemUnifiedSystem:
    """ONE unified system - all AI agents working together"""
    
    def __init__(self):
        self.version = "2.0.0-Unified"
        self.start_time = datetime.now()
        
        # Core configuration
        self.config = {
            'openai_key': os.getenv('OPENAI_API_KEY'),
            'gemini_key': os.getenv('GEMINI_API_KEY'),
            'weather_key': os.getenv('WEATHER_API_KEY'),
            'debug': os.getenv('DEBUG', 'true').lower() == 'true'
        }
        
        # System state
        self.is_running = False
        self.user_context = {}
        self.conversation_history = []
        
        # AI agents status
        self.ai_agents = {
            'amazon_q': {'active': True, 'role': 'coordinator'},
            'claude': {'active': True, 'role': 'accessibility'},
            'gemini': {'active': True, 'role': 'ai_processing'},
            'tabnine': {'active': True, 'role': 'performance'},
            'copilot': {'active': True, 'role': 'voice'},
            'cursor': {'active': True, 'role': 'architecture'}
        }
        
        self._setup_logging()
        
    def _setup_logging(self):
        """Setup logging system"""
        log_dir = Path('./logs')
        log_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=logging.DEBUG if self.config['debug'] else logging.INFO,
            format='%(asctime)s - [%(name)s] - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_dir / 'gem_unified.log'),
                logging.StreamHandler() if self.config['debug'] else logging.NullHandler()
            ]
        )
        
        self.logger = logging.getLogger("GemUnified")
        
    async def initialize_system(self):
        """Initialize all system components"""
        print("🔥 GEM OS - UNIFIED SYSTEM STARTING...")
        print(f"🎯 Version: {self.version}")
        print(f"⏰ Started: {self.start_time}")
        
        # Check configuration
        config_ok = await self._check_configuration()
        
        # Initialize components
        audio_ok = await self._initialize_audio()
        ai_ok = await self._initialize_ai()
        accessibility_ok = await self._initialize_accessibility()
        
        system_ready = config_ok and (audio_ok or ai_ok)  # Need at least config + (audio OR ai)
        
        print(f"\n📊 SYSTEM STATUS:")
        print(f"   Configuration: {'✅' if config_ok else '❌'}")
        print(f"   Audio System: {'✅' if audio_ok else '⚠️'}")
        print(f"   AI Processing: {'✅' if ai_ok else '❌'}")
        print(f"   Accessibility: {'✅' if accessibility_ok else '⚠️'}")
        print(f"   Overall: {'✅ READY' if system_ready else '❌ LIMITED'}")
        
        return system_ready
        
    async def _check_configuration(self):
        """Check system configuration"""
        print("\n🔧 Checking configuration...")
        
        config_issues = []
        
        if not self.config['openai_key']:
            config_issues.append("OpenAI API key missing")
        if not self.config['gemini_key']:
            config_issues.append("Gemini API key missing")
            
        if config_issues:
            print("⚠️ Configuration issues:")
            for issue in config_issues:
                print(f"   - {issue}")
            print("   System will run in limited mode")
            return False
        else:
            print("✅ Configuration OK")
            return True
            
    async def _initialize_audio(self):
        """Initialize audio system (simplified)"""
        print("\n🎤 Initializing audio system...")
        
        try:
            # Check if audio libraries are available
            import pyaudio
            
            # Basic audio test
            p = pyaudio.PyAudio()
            device_count = p.get_device_count()
            p.terminate()
            
            if device_count > 0:
                print(f"✅ Audio system ready ({device_count} devices)")
                return True
            else:
                print("⚠️ No audio devices found")
                return False
                
        except ImportError:
            print("⚠️ PyAudio not available - install with: pip install pyaudio")
            return False
        except Exception as e:
            print(f"⚠️ Audio system error: {e}")
            return False
            
    async def _initialize_ai(self):
        """Initialize AI processing"""
        print("\n🧠 Initializing AI processing...")
        
        ai_available = []
        
        # Check OpenAI
        if self.config['openai_key']:
            try:
                import openai
                ai_available.append("OpenAI")
            except ImportError:
                print("⚠️ OpenAI library not available")
                
        # Check Gemini
        if self.config['gemini_key']:
            try:
                import google.generativeai as genai
                ai_available.append("Gemini")
            except ImportError:
                print("⚠️ Gemini library not available")
                
        if ai_available:
            print(f"✅ AI processing ready: {', '.join(ai_available)}")
            return True
        else:
            print("❌ No AI processing available")
            return False
            
    async def _initialize_accessibility(self):
        """Initialize accessibility features"""
        print("\n♿ Initializing accessibility...")
        
        accessibility_features = []
        
        # Check for screen reader support
        if os.path.exists('/usr/bin/orca'):
            accessibility_features.append("Orca")
            
        # Check for text-to-speech
        try:
            import pyttsx3
            accessibility_features.append("TTS")
        except ImportError:
            pass
            
        if accessibility_features:
            print(f"✅ Accessibility ready: {', '.join(accessibility_features)}")
            return True
        else:
            print("⚠️ Limited accessibility support")
            return False
            
    async def process_user_input(self, user_input: str) -> str:
        """Process user input and generate response"""
        start_time = time.time()
        
        # Add to conversation history
        self.conversation_history.append({
            'user': user_input,
            'timestamp': datetime.now().isoformat()
        })
        
        # Generate AI response
        response = await self._generate_ai_response(user_input)
        
        # Add response to history
        self.conversation_history.append({
            'assistant': response,
            'timestamp': datetime.now().isoformat(),
            'response_time': time.time() - start_time
        })
        
        # Keep history manageable
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]
            
        return response
        
    async def _generate_ai_response(self, user_input: str) -> str:
        """Generate AI response using available AI services"""
        
        # Try OpenAI first
        if self.config['openai_key']:
            try:
                import openai
                
                client = openai.AsyncOpenAI(api_key=self.config['openai_key'])
                
                # Build context from conversation history
                messages = []
                for entry in self.conversation_history[-10:]:  # Last 10 exchanges
                    if 'user' in entry:
                        messages.append({'role': 'user', 'content': entry['user']})
                    elif 'assistant' in entry:
                        messages.append({'role': 'assistant', 'content': entry['assistant']})
                        
                # Add current message
                messages.append({'role': 'user', 'content': user_input})
                
                # Add system message for accessibility
                system_message = {
                    'role': 'system',
                    'content': 'You are GEM, an accessibility-first AI assistant. Provide helpful, clear responses optimized for screen readers and voice interaction. Be empathetic and supportive.'
                }
                messages.insert(0, system_message)
                
                response = await client.chat.completions.create(
                    model='gpt-4o-mini',
                    messages=messages,
                    max_tokens=500,
                    temperature=0.7
                )
                
                return response.choices[0].message.content
                
            except Exception as e:
                self.logger.error(f"OpenAI error: {e}")
                
        # Try Gemini as fallback
        if self.config['gemini_key']:
            try:
                import google.generativeai as genai
                
                genai.configure(api_key=self.config['gemini_key'])
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                # Build context
                context = "You are GEM, an accessibility-first AI assistant.\n\n"
                for entry in self.conversation_history[-5:]:
                    if 'user' in entry:
                        context += f"User: {entry['user']}\n"
                    elif 'assistant' in entry:
                        context += f"Assistant: {entry['assistant']}\n"
                        
                context += f"User: {user_input}\nAssistant:"
                
                response = await asyncio.to_thread(model.generate_content, context)
                return response.text
                
            except Exception as e:
                self.logger.error(f"Gemini error: {e}")
                
        # Fallback response
        return "I'm having trouble connecting to AI services right now. Please check your API keys and try again."
        
    async def speak_response(self, text: str):
        """Speak response using text-to-speech"""
        try:
            import pyttsx3
            
            engine = pyttsx3.init()
            
            # Configure voice for accessibility
            voices = engine.getProperty('voices')
            if voices:
                # Prefer female voice
                for voice in voices:
                    if 'female' in voice.name.lower():
                        engine.setProperty('voice', voice.id)
                        break
                        
            engine.setProperty('rate', 150)  # Slower for accessibility
            engine.setProperty('volume', 0.9)
            
            # Speak in separate thread to avoid blocking
            await asyncio.to_thread(engine.say, text)
            await asyncio.to_thread(engine.runAndWait)
            
        except ImportError:
            print("⚠️ Text-to-speech not available - install with: pip install pyttsx3")
        except Exception as e:
            self.logger.error(f"TTS error: {e}")
            
    async def run_interactive_session(self):
        """Run interactive session with user"""
        print("\n💬 GEM OS Interactive Session")
        print("🎤 Type your messages or 'quit' to exit")
        print("🔥 All AI agents are working together!")
        
        self.is_running = True
        
        while self.is_running:
            try:
                # Get user input
                user_input = input("\n💬 You: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'stop']:
                    print("👋 Goodbye! GEM OS session ended.")
                    break
                    
                if not user_input:
                    continue
                    
                # Process input
                print("🤖 Processing...")
                response = await self.process_user_input(user_input)
                
                # Display response
                print(f"💎 GEM: {response}")
                
                # Speak response if TTS available
                await self.speak_response(response)
                
            except KeyboardInterrupt:
                print("\n👋 Session interrupted. Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                self.logger.error(f"Session error: {e}")
                
        self.is_running = False
        
    def get_system_status(self) -> Dict[str, Any]:
        """Get current system status"""
        return {
            'version': self.version,
            'uptime': (datetime.now() - self.start_time).total_seconds(),
            'ai_agents': self.ai_agents,
            'conversation_length': len(self.conversation_history),
            'config_status': {
                'openai_configured': bool(self.config['openai_key']),
                'gemini_configured': bool(self.config['gemini_key']),
                'weather_configured': bool(self.config['weather_key'])
            }
        }

async def main():
    """Main entry point"""
    print("💎" + "=" * 60)
    print("💎 GEM OS - UNIFIED SYSTEM")
    print("💎 All AI agents working together in ONE system")
    print("💎 Accessibility-first design for everyone")
    print("💎" + "=" * 60)
    
    # Create and initialize system
    gem_system = GemUnifiedSystem()
    
    try:
        # Initialize
        system_ready = await gem_system.initialize_system()
        
        if system_ready:
            # Run interactive session
            await gem_system.run_interactive_session()
        else:
            print("\n❌ System not ready. Please check configuration and dependencies.")
            
            # Show status
            status = gem_system.get_system_status()
            print(f"\n📊 System Status: {json.dumps(status, indent=2)}")
            
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        gem_system.logger.error(f"Fatal error: {e}")
    finally:
        print("\n💎 GEM OS session complete")

if __name__ == "__main__":
    asyncio.run(main())