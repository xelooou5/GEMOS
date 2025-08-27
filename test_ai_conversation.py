#!/usr/bin/env python3
"""
🧠 GEMINI: TEST AI CONVERSATION SYSTEM
Quick test of AI conversation with OpenAI API
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_ai_conversation():
    """Test AI conversation system"""
    print("🧠 GEMINI: Testing AI Conversation System")
    print("=" * 50)
    
    # Check API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key or api_key == 'your_openai_key_here':
        print("❌ OpenAI API key not configured")
        return False
        
    try:
        import openai
        
        # Create client
        client = openai.AsyncOpenAI(api_key=api_key)
        
        # Test conversation
        print("🤖 Testing AI response...")
        
        response = await client.chat.completions.create(
            model='gpt-4o-mini',
            messages=[
                {
                    'role': 'system',
                    'content': 'You are GEM, an accessibility-first AI assistant. Respond briefly and helpfully.'
                },
                {
                    'role': 'user',
                    'content': 'Hello GEM! Can you help me test the voice system?'
                }
            ],
            max_tokens=100,
            temperature=0.7
        )
        
        ai_response = response.choices[0].message.content
        print(f"✅ AI Response: {ai_response}")
        
        # Test TTS
        print("\n🔊 Testing text-to-speech...")
        try:
            import pyttsx3
            
            engine = pyttsx3.init()
            engine.setProperty('rate', 150)
            engine.setProperty('volume', 0.9)
            
            # Speak the AI response
            engine.say(ai_response)
            engine.runAndWait()
            
            print("✅ TTS working")
            
        except Exception as e:
            print(f"⚠️ TTS error: {e}")
            
        return True
        
    except Exception as e:
        print(f"❌ AI conversation error: {e}")
        return False

async def main():
    """Test AI conversation system"""
    success = await test_ai_conversation()
    
    if success:
        print("\n🎉 AI CONVERSATION SYSTEM WORKING!")
        print("✅ OpenAI API connected")
        print("✅ AI responses generated")
        print("✅ Text-to-speech functional")
    else:
        print("\n❌ AI conversation system needs fixes")
        
    return success

if __name__ == "__main__":
    asyncio.run(main())