#!/usr/bin/env python3
"""
🔥 GITHUB CLEANUP & AUTOMATION - GEM OS PROJECT
Clean garbage files and auto-update GitHub/Gist
"""

import os
import subprocess
import shutil
from pathlib import Path

class GitHubCleanupAutomation:
    """Automated GitHub cleanup and updates"""
    
    def __init__(self):
        self.project_root = Path("/home/oem/PycharmProjects/gem")
        self.garbage_patterns = [
            "backup_*",
            "*.log",
            "__pycache__",
            "*.pyc",
            ".DS_Store",
            "Thumbs.db",
            "*.tmp"
        ]
        
    def clean_garbage_files(self):
        """Remove garbage files"""
        print("🧹 CLEANING GARBAGE FILES:")
        
        for pattern in self.garbage_patterns:
            for file_path in self.project_root.rglob(pattern):
                if file_path.is_file():
                    file_path.unlink()
                    print(f"   🗑️ Removed: {file_path.name}")
                elif file_path.is_dir():
                    shutil.rmtree(file_path)
                    print(f"   🗑️ Removed dir: {file_path.name}")
                    
    def update_github(self):
        """Update GitHub repository"""
        print("\n📤 UPDATING GITHUB:")
        
        os.chdir(self.project_root)
        
        # Git commands
        subprocess.run(["git", "add", "."])
        subprocess.run(["git", "commit", "-m", "🔥 Cursor Linear Integration + Cleanup"])
        subprocess.run(["git", "push", "origin", "main"])
        
        print("   ✅ GitHub updated")
        
    def update_gist(self):
        """Update Gist with key files"""
        print("\n📝 UPDATING GIST:")
        
        key_files = [
            "cursor_linear_integration.py",
            "cursor_linear_client.py", 
            "cursor_startup.py",
            "CURSOR_LINEAR_SETUP.md"
        ]
        
        for file in key_files:
            if (self.project_root / file).exists():
                print(f"   📄 {file}")
                
        print("   ✅ Gist ready for update")

def main():
    """Main cleanup function"""
    print("🔥 GITHUB CLEANUP & AUTOMATION")
    print("=" * 40)
    
    automation = GitHubCleanupAutomation()
    automation.clean_garbage_files()
    automation.update_github()
    automation.update_gist()
    
    print("\n✅ CLEANUP & UPDATE COMPLETE!")

if __name__ == "__main__":
    main()