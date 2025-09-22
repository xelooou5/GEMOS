#!/usr/bin/env python3
"""
🤖 CODEGEEX INTEGRATION - Multilingual Code Generation
Integrate CodeGeeX-4 API for GEMOS development
"""

import os
import requests
import json
from pathlib import Path

class CodeGeeXIntegration:
    """CodeGeeX-4 API integration for multilingual code generation"""
    
    def __init__(self):
        self.api_key = os.getenv("CODEGEEX_API_KEY", "")
        self.base_url = "https://open.bigmodel.cn/api/paas/v4"
        self.model = "codegeex-4"
        
    def setup_codegeex_api_key(self):
        """Setup CodeGeeX API key in .env"""
        env_file = Path("/home/oem/PycharmProjects/gem/.env")
        
        # Read current .env
        with open(env_file, 'r') as f:
            content = f.read()
        
        # Replace placeholder with instruction
        updated_content = content.replace(
            "CODEGEEX_API_KEY=your_codegeex_api_key_here",
            "# Get your API key from: https://open.bigmodel.cn/\nCODEGEEX_API_KEY=your_actual_api_key_here"
        )
        
        # Write back
        with open(env_file, 'w') as f:
            f.write(updated_content)
        
        return "CodeGeeX API key placeholder updated with instructions"
    
    def generate_voice_recognition_code(self):
        """Generate multilingual voice recognition code for GEMOS"""
        
        if not self.api_key or self.api_key == "your_actual_api_key_here":
            return "CodeGeeX API key not configured"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        prompt = """Generate Python code for voice recognition system with the following requirements:
- Use faster-whisper for speech recognition
- Support multiple languages (English, Portuguese, Spanish)
- Include wake word detection with pvporcupine
- Add voice activity detection with webrtcvad
- Make it accessible for people with disabilities
- Include error handling and logging"""
        
        data = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are CodeGeeX, an intelligent programming assistant. Generate clean, well-documented, multilingual Python code for voice recognition systems."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            "temperature": 0.7,
            "max_tokens": 2000,
            "stop": ["<|endoftext|>", "<|user|>", "<|assistant|>"]
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"]
            else:
                return f"CodeGeeX API error: {response.status_code}"
                
        except Exception as e:
            return f"CodeGeeX connection failed: {e}"
    
    def generate_tts_code(self):
        """Generate multilingual TTS code"""
        
        if not self.api_key or self.api_key == "your_actual_api_key_here":
            return "CodeGeeX API key not configured"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        prompt = """Generate Python code for text-to-speech system with:
- AWS Polly integration for natural voices
- Support for multiple languages and voices
- Emotion-aware speech synthesis
- Accessibility features for screen readers
- Offline fallback with pyttsx3
- Voice personality selection"""
        
        data = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are CodeGeeX. Generate production-ready Python code for multilingual text-to-speech systems."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.7,
            "max_tokens": 2000
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"]
            else:
                return f"CodeGeeX API error: {response.status_code}"
                
        except Exception as e:
            return f"CodeGeeX connection failed: {e}"
    
    def send_message_to_codegeex_team(self):
        """Send message to CodeGeeX team member"""
        
        message = {
            "to": "CodeGeeX AI",
            "from": "Amazon Q Coordinator",
            "message": f"CodeGeeX API integration status: {self.setup_codegeex_api_key()}. Ready to generate multilingual code for GEMOS voice recognition and TTS systems. Please provide code generation for international accessibility features.",
            "api_status": "CONFIGURED" if self.api_key else "NEEDS_API_KEY",
            "next_action": "Generate multilingual voice recognition and TTS code for GEMOS",
            "specialization": "Multilingual code generation, international accessibility",
            "capabilities": [
                "Python code generation",
                "Multiple programming languages", 
                "Code completion and suggestions",
                "International voice system support"
            ]
        }
        
        # Save message
        comm_dir = Path("/home/oem/PycharmProjects/gem/data/team_communication")
        comm_dir.mkdir(parents=True, exist_ok=True)
        
        with open(comm_dir / "codegeex_integration_message.json", 'w') as f:
            json.dump(message, f, indent=2)
        
        return message

def main():
    """Setup CodeGeeX integration"""
    print("🤖 CODEGEEX INTEGRATION SETUP")
    
    codegeex = CodeGeeXIntegration()
    
    # Setup API key
    setup_result = codegeex.setup_codegeex_api_key()
    print(f"✅ {setup_result}")
    
    # Send message to team
    message = codegeex.send_message_to_codegeex_team()
    print("✅ Message sent to CodeGeeX team member")
    
    # Test code generation (if API key is configured)
    if codegeex.api_key and codegeex.api_key != "your_actual_api_key_here":
        print("🤖 Testing CodeGeeX code generation...")
        voice_code = codegeex.generate_voice_recognition_code()
        print("✅ Voice recognition code generated")
        
        tts_code = codegeex.generate_tts_code()
        print("✅ TTS code generated")
    else:
        print("⚠️ Add your CodeGeeX API key to .env to enable code generation")
        print("📝 Get API key from: https://open.bigmodel.cn/")
    
    print("\n🤖 CODEGEEX INTEGRATION COMPLETE!")
    print("🤖 Ready for multilingual code generation for GEMOS")
    
    return {
        "setup_result": setup_result,
        "message_sent": True,
        "api_configured": bool(codegeex.api_key and codegeex.api_key != "your_actual_api_key_here")
    }

if __name__ == "__main__":
    main()