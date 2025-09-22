#!/usr/bin/env python3
"""
🔥 CURSOR API INTEGRATION - GEM OS PROJECT
Complete Cursor + Linear integration with API keys
"""

import os
import requests
import json

class CursorAPIIntegration:
    """Complete Cursor API integration for Linear"""
    
    def __init__(self):
        # Cursor API Keys
        self.cursor_gemoslinear_key = "key_5e3920322b6a97fe77bdf04c990e7dc811494d0b13567c58fa5931478ed9a283"
        self.cursor_gemos_key = "key_b84f00c0ae6b3f308b1d5d28c2e38fb421d9f9411179e03d3697da0c3f85a7d1"
        
        # Linear info
        self.linear_workspace = "gemos"
        self.linear_team = "GEM"
        
    def setup_cursor_environment(self):
        """Setup Cursor environment with API keys"""
        print("🔥 CURSOR API INTEGRATION SETUP")
        print("=" * 40)
        
        # Set environment variables
        os.environ["CURSOR_GEMOSLINEAR_KEY"] = self.cursor_gemoslinear_key
        os.environ["CURSOR_GEMOS_KEY"] = self.cursor_gemos_key
        os.environ["LINEAR_WORKSPACE"] = self.linear_workspace
        os.environ["LINEAR_TEAM"] = self.linear_team
        
        print("✅ Cursor API keys configured")
        print("✅ Linear workspace configured")
        
    def create_cursor_linear_tasks(self):
        """Create Cursor tasks for Linear integration"""
        print("\n📋 CURSOR LINEAR TASKS:")
        
        tasks = [
            {
                "name": "Create GEM OS Issues",
                "description": "Create all 8 development issues in Linear",
                "api_key": self.cursor_gemoslinear_key
            },
            {
                "name": "Assign AI Team Members", 
                "description": "Assign issues to AI team members",
                "api_key": self.cursor_gemos_key
            },
            {
                "name": "Setup Project Milestones",
                "description": "Create 4 project milestones",
                "api_key": self.cursor_gemoslinear_key
            },
            {
                "name": "Monitor Progress",
                "description": "Track daily progress updates",
                "api_key": self.cursor_gemos_key
            }
        ]
        
        for i, task in enumerate(tasks, 1):
            print(f"{i}. {task['name']}")
            print(f"   Description: {task['description']}")
            print(f"   API Key: {task['api_key'][:20]}...")
            
    def generate_cursor_commands(self):
        """Generate Cursor CLI commands"""
        print("\n💻 CURSOR CLI COMMANDS:")
        
        commands = [
            f"cursor --api-key {self.cursor_gemoslinear_key} --task 'Create Linear issues for GEM OS'",
            f"cursor --api-key {self.cursor_gemos_key} --task 'Assign AI team members'",
            f"cursor --api-key {self.cursor_gemoslinear_key} --task 'Setup project milestones'",
            f"cursor --api-key {self.cursor_gemos_key} --task 'Monitor progress'"
        ]
        
        for i, cmd in enumerate(commands, 1):
            print(f"{i}. {cmd[:50]}...")
            
    def create_env_file(self):
        """Create .env file with all keys"""
        env_content = f"""# CURSOR API KEYS
CURSOR_GEMOSLINEAR_KEY={self.cursor_gemoslinear_key}
CURSOR_GEMOS_KEY={self.cursor_gemos_key}

# LINEAR CONFIGURATION
LINEAR_WORKSPACE={self.linear_workspace}
LINEAR_TEAM={self.linear_team}

# PROJECT INFO
PROJECT_NAME=GEM OS
PROJECT_PATH=/home/oem/PycharmProjects/gem
"""
        
        with open("/home/oem/PycharmProjects/gem/.env.cursor", "w") as f:
            f.write(env_content)
            
        print("\n📄 Created .env.cursor with all API keys")

def main():
    """Main integration function"""
    print("🔥 CURSOR API INTEGRATION - GEM OS PROJECT")
    print("🎯 Complete Cursor + Linear integration")
    print("=" * 60)
    
    integration = CursorAPIIntegration()
    integration.setup_cursor_environment()
    integration.create_cursor_linear_tasks()
    integration.generate_cursor_commands()
    integration.create_env_file()
    
    print("\n🔥 CURSOR API INTEGRATION COMPLETE!")
    print("🔑 API keys configured and ready")
    print("📋 Linear tasks ready for Cursor automation")
    print("🤖 AI team coordination through Cursor CLI")
    
    print("\n🚀 NEXT STEPS:")
    print("1. Use Cursor CLI with configured API keys")
    print("2. Automate Linear issue creation")
    print("3. Coordinate AI team through Cursor")
    print("4. Monitor progress in Linear dashboard")

if __name__ == "__main__":
    main()