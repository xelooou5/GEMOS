#!/usr/bin/env python3
"""
🔥 PYCHARM + CURSOR CLI INTEGRATION - GEM OS PROJECT
Integrate PyCharm with Cursor CLI for Linear automation
"""

import subprocess
import os
import json

class PyCharmCursorIntegration:
    """PyCharm + Cursor CLI integration"""
    
    def __init__(self):
        self.project_path = "/home/oem/PycharmProjects/gem"
        
    def setup_cursor_in_pycharm(self):
        """Setup Cursor CLI integration in PyCharm"""
        print("🔥 PYCHARM + CURSOR CLI INTEGRATION")
        print("=" * 40)
        
        # Create external tool configuration for PyCharm
        external_tool_config = {
            "name": "Cursor Linear Integration",
            "description": "Run Cursor CLI for Linear tasks",
            "program": "cursor",
            "arguments": "--task 'Linear integration for GEM OS'",
            "workingDirectory": "$ProjectFileDir$"
        }
        
        print("⚙️ PYCHARM EXTERNAL TOOL SETUP:")
        print("1. Go to File > Settings > Tools > External Tools")
        print("2. Click '+' to add new tool")
        print("3. Configure:")
        print(f"   Name: {external_tool_config['name']}")
        print(f"   Program: {external_tool_config['program']}")
        print(f"   Arguments: {external_tool_config['arguments']}")
        print(f"   Working Directory: {external_tool_config['workingDirectory']}")
        
    def create_cursor_tasks(self):
        """Create Cursor CLI tasks for Linear"""
        print("\n📋 CURSOR CLI TASKS:")
        
        tasks = [
            "cursor --task 'Create Linear issues for GEM OS AI team'",
            "cursor --task 'Setup GitHub integration with Linear'", 
            "cursor --task 'Coordinate AI team assignments'",
            "cursor --task 'Monitor project progress in Linear'"
        ]
        
        for i, task in enumerate(tasks, 1):
            print(f"{i}. {task}")
            
    def run_cursor_integration(self):
        """Run Cursor CLI integration"""
        print("\n🚀 RUNNING CURSOR CLI INTEGRATION:")
        
        os.chdir(self.project_path)
        
        # Open project in Cursor
        subprocess.run(["cursor", "."])
        
        print("✅ Cursor opened with GEM OS project")
        print("🎯 Use Cursor AI to automate Linear tasks")

def main():
    """Main function"""
    integration = PyCharmCursorIntegration()
    integration.setup_cursor_in_pycharm()
    integration.create_cursor_tasks()
    integration.run_cursor_integration()
    
    print("\n🔥 PYCHARM + CURSOR INTEGRATION COMPLETE!")
    print("📋 Use Cursor CLI from PyCharm for Linear automation")

if __name__ == "__main__":
    main()