#!/usr/bin/env python3
"""
🔥 LINEAR TEAM AUTHENTICATION - GEM OS PROJECT
Setup authentication for all AI team members
Join URL: https://linear.app/gemos/join/6726367e02684d2b31770912dcbf4e75?s=5
"""

import requests
import json
from typing import Dict, List

class LinearTeamAuth:
    """Linear team authentication and API key management"""
    
    def __init__(self):
        self.join_url = "https://linear.app/gemos/join/6726367e02684d2b31770912dcbf4e75?s=5"
        self.workspace = "gemos"
        self.team_key = "GEM"
        
    def show_authentication_steps(self):
        """Show authentication steps for team members"""
        print("🔥 LINEAR TEAM AUTHENTICATION SETUP")
        print("=" * 50)
        
        print(f"🔗 Join URL: {self.join_url}")
        print(f"🏢 Workspace: {self.workspace}")
        print(f"👥 Team: {self.team_key}")
        
        print("\n📋 AUTHENTICATION STEPS:")
        print("1. Visit the join URL above")
        print("2. Create Linear account or sign in")
        print("3. Join the GEMOS workspace")
        print("4. Access the GEM team")
        print("5. Go to Settings > API > Personal API tokens")
        print("6. Create new API token")
        print("7. Copy the token for your AI agent")
        
    def generate_api_key_instructions(self):
        """Generate API key creation instructions"""
        print("\n🔑 API KEY CREATION INSTRUCTIONS:")
        print("=" * 40)
        
        ai_agents = [
            "Amazon Q - System Coordinator",
            "Claude - Accessibility Specialist", 
            "Cursor - Security & Architecture",
            "TabNine - Performance Engineer",
            "Copilot - Voice Interface Developer",
            "Gemini - AI Intelligence Developer"
        ]
        
        for agent in ai_agents:
            print(f"\n👤 {agent}:")
            print("   1. Visit: https://linear.app/gemos/settings/api")
            print("   2. Click 'Create new token'")
            print(f"   3. Name: '{agent} - GEM OS Project'")
            print("   4. Select scopes: read, write")
            print("   5. Copy token to .env file")
            
    def create_env_template(self):
        """Create .env template for API keys"""
        env_content = """# LINEAR API KEYS FOR AI TEAM MEMBERS
# Get keys from: https://linear.app/gemos/settings/api

# System Coordinator
AMAZON_Q_LINEAR_KEY=your_amazon_q_key_here

# Accessibility Specialist  
CLAUDE_LINEAR_KEY=your_claude_key_here

# Security & Architecture
CURSOR_LINEAR_KEY=your_cursor_key_here

# Performance Engineer
TABNINE_LINEAR_KEY=your_tabnine_key_here

# Voice Interface Developer
COPILOT_LINEAR_KEY=your_copilot_key_here

# AI Intelligence Developer
GEMINI_LINEAR_KEY=your_gemini_key_here

# Workspace info
LINEAR_WORKSPACE=gemos
LINEAR_TEAM=GEM
"""
        
        with open("/home/oem/PycharmProjects/gem/.env.linear", "w") as f:
            f.write(env_content)
            
        print("\n📄 Created .env.linear template")
        print("   • Fill in your API keys")
        print("   • Each AI agent needs their own key")
        
    def test_api_connection(self, api_key: str) -> bool:
        """Test Linear API connection"""
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        query = '''
        query Me {
          viewer {
            id
            name
            email
          }
        }
        '''
        
        try:
            response = requests.post(
                "https://api.linear.app/graphql",
                headers=headers,
                json={"query": query}
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'data' in data and 'viewer' in data['data']:
                    return True
            return False
        except:
            return False

def main():
    """Main function"""
    auth = LinearTeamAuth()
    auth.show_authentication_steps()
    auth.generate_api_key_instructions()
    auth.create_env_template()
    
    print("\n🔥 LINEAR AUTHENTICATION SETUP COMPLETE!")
    print("📋 Follow the instructions above to get API keys")
    print("🔑 Fill in the .env.linear file with your keys")

if __name__ == "__main__":
    main()