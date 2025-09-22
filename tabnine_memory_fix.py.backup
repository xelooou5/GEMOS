#!/usr/bin/env python3
"""
🧠 TABNINE - LEARN_MEMORIZE PILLAR IMPLEMENTATION
TabNine fixes memory and learning system
"""

import json
import sqlite3
from pathlib import Path

class TabNineMemoryFix:
    def __init__(self):
        self.project_root = Path("/home/oem/PycharmProjects/gem")
        self.db_path = self.project_root / "data" / "memory.db"
        
    def fix_memory_pillar(self):
        """🧠 TABNINE: Implement LEARN_MEMORIZE pillar"""
        print("🧠 TABNINE WORKING ON LEARN_MEMORIZE PILLAR")
        
        # Create memory database
        os.makedirs(self.db_path.parent, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create memory tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY,
                user_input TEXT,
                response TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_preferences (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        
        # Create memory manager
        memory_code = '''
import sqlite3
from pathlib import Path

class MemoryManager:
    def __init__(self):
        self.db_path = Path("data/memory.db")
        
    def remember_conversation(self, user_input, response):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO conversations (user_input, response) VALUES (?, ?)", 
                      (user_input, response))
        conn.commit()
        conn.close()
        
    def get_user_preference(self, key):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM user_preferences WHERE key = ?", (key,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None
'''
        
        with open(self.project_root / "core" / "memory_manager.py", "w") as f:
            f.write(memory_code)
        
        print("✅ TABNINE: LEARN_MEMORIZE pillar implemented!")
        return True

if __name__ == "__main__":
    tabnine = TabNineMemoryFix()
    tabnine.fix_memory_pillar()