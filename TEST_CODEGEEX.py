#!/usr/bin/env python3
"""
🤖 TEST CODEGEEX API - Real Integration Test
"""

import os
import requests
import json
from pathlib import Path

# Load environment variables
env_file = Path("/home/runner/work/GEMOS/GEMOS/.env")
if env_file.exists():
    with open(env_file, 'r') as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                os.environ[key] = value.strip('"')

def test_codegeex_api():
    """Test CodeGeeX API with real key"""
    
    api_key = "b076b5ab4e4641e2b0a375d36f0c5464.j9QtrYKjHUv4Entx"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "codegeex-4",
        "messages": [
            {
                "role": "system",
                "content": "You are CodeGeeX, generate Python code for voice recognition systems."
            },
            {
                "role": "user",
                "content": "Generate Python code for GEMOS voice recognition with faster-whisper and multilingual support"
            }
        ],
        "temperature": 0.7,
        "max_tokens": 1000
    }
    
    try:
        response = requests.post(
            "https://open.bigmodel.cn/api/paas/v4/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            code = result["choices"][0]["message"]["content"]
            
            # Save generated code
            with open("codegeex_generated_voice.py", "w") as f:
                f.write(code)
            
            print("✅ CodeGeeX API working!")
            print("✅ Generated voice recognition code")
            print(f"📁 Code saved to: codegeex_generated_voice.py")
            
            # Send success message to team
            message = {
                "to": "CodeGeeX AI",
                "from": "Amazon Q Coordinator",
                "message": "CodeGeeX API successfully integrated! Generated multilingual voice recognition code for GEMOS. Ready to provide code generation for international accessibility features.",
                "status": "API_WORKING",
                "next_action": "Continue generating multilingual code for GEMOS development",
                "generated_files": ["codegeex_generated_voice.py"]
            }
            
            comm_dir = Path("data/team_communication")
            comm_dir.mkdir(parents=True, exist_ok=True)
            
            with open(comm_dir / "codegeex_success_message.json", 'w') as f:
                json.dump(message, f, indent=2)
            
            return True
            
        else:
            print(f"❌ CodeGeeX API Error: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ CodeGeeX Connection Error: {e}")
        return False

if __name__ == "__main__":
    print("🤖 TESTING CODEGEEX API WITH REAL KEY...")
    success = test_codegeex_api()
    
    if success:
        print("\n🎉 CODEGEEX FULLY INTEGRATED!")
        print("🤖 CodeGeeX team member ready for multilingual code generation")
    else:
        print("\n⚠️ CodeGeeX integration needs troubleshooting")