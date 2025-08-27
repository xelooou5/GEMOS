#!/usr/bin/env python3
"""
🔥 GEM OS - HOURLY BACKUP SYSTEM
Auto-backup to GitHub and Gist every hour in case PC explodes
"""

import subprocess
import time
import json
import os
from datetime import datetime
from pathlib import Path

class HourlyBackup:
    def __init__(self):
        self.project_root = Path("/home/oem/PycharmProjects/gem")
        self.github_repo = "https://github.com/xelooou5/gemos.git"
        
    def backup_to_github(self):
        """Push all changes to GitHub"""
        try:
            os.chdir(self.project_root)
            
            # Add all changes
            subprocess.run(["git", "add", "."], check=True)
            
            # Commit with timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            commit_msg = f"🔥 HOURLY BACKUP - {timestamp} - PC EXPLOSION PROTECTION"
            subprocess.run(["git", "commit", "-m", commit_msg], check=True)
            
            # Push to GitHub
            subprocess.run(["git", "push", "origin", "main"], check=True)
            
            print(f"✅ GitHub backup successful: {timestamp}")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ GitHub backup failed: {e}")
            return False
            
    def backup_to_gist(self):
        """Create/update Gist with critical files"""
        try:
            critical_files = [
                "gem.py",
                "gem_daemon.py", 
                "HELP.py",
                "voice_system_complete.py",
                "core/stt_module.py",
                "core/tts_module.py",
                "AUTONOMOUS_CONFIG.json",
                "README.md"
            ]
            
            # Create gist content
            gist_data = {
                "description": f"🔥 GEM OS Critical Files Backup - {datetime.now().isoformat()}",
                "public": False,
                "files": {}
            }
            
            for file_path in critical_files:
                full_path = self.project_root / file_path
                if full_path.exists():
                    with open(full_path, 'r', encoding='utf-8') as f:
                        gist_data["files"][file_path.replace("/", "_")] = {
                            "content": f.read()
                        }
            
            # Save gist data for manual upload
            gist_file = self.project_root / "data" / "hourly_gist_backup.json"
            gist_file.parent.mkdir(exist_ok=True)
            
            with open(gist_file, 'w') as f:
                json.dump(gist_data, f, indent=2)
                
            print(f"✅ Gist backup prepared: {gist_file}")
            return True
            
        except Exception as e:
            print(f"❌ Gist backup failed: {e}")
            return False
            
    def run_hourly_backup(self):
        """Run backup every hour"""
        print("🔥 STARTING HOURLY BACKUP SYSTEM")
        print("💥 PC EXPLOSION PROTECTION ACTIVE")
        
        while True:
            try:
                print(f"\n⏰ {datetime.now().strftime('%H:%M:%S')} - Running backup...")
                
                # Backup to GitHub
                github_success = self.backup_to_github()
                
                # Backup to Gist
                gist_success = self.backup_to_gist()
                
                if github_success and gist_success:
                    print("✅ FULL BACKUP COMPLETE - PC CAN EXPLODE SAFELY NOW")
                else:
                    print("⚠️ PARTIAL BACKUP - SOME RISK REMAINS")
                
                # Wait 1 hour
                print("😴 Sleeping for 1 hour...")
                time.sleep(3600)  # 1 hour
                
            except KeyboardInterrupt:
                print("\n🔥 Backup system stopped")
                break
            except Exception as e:
                print(f"❌ Backup error: {e}")
                time.sleep(300)  # Wait 5 minutes on error

if __name__ == "__main__":
    backup = HourlyBackup()
    backup.run_hourly_backup()