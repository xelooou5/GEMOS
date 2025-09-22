#!/usr/bin/env python3
"""
🔥 CHAT HISTORY COORDINATOR - FEEDS ALL AGENTS CONTINUOUSLY
Reads all chat history and sends work to agents so queue never = 0
"""

import asyncio
import json
import os
from pathlib import Path
from datetime import datetime

class ChatHistoryCoordinator:
    def __init__(self):
        self.agents_dir = Path("data/unified_ai_team/agents")
        self.chat_dirs = [
            Path.home() / ".continue/sessions",
            Path.home() / ".cursor/chat",
            Path.home() / ".amazonq/chat",
            Path("/home/runner/work/GEMOS/GEMOS")
        ]
        self.work_counter = 0
        
    async def scan_all_chats(self):
        """Scan all chat history files"""
        chat_files = []
        
        for chat_dir in self.chat_dirs:
            if chat_dir.exists():
                for file in chat_dir.rglob("*"):
                    if file.is_file() and any(ext in file.suffix for ext in ['.json', '.md', '.txt', '.log']):
                        chat_files.append(file)
                        
        print(f"📚 Found {len(chat_files)} chat/history files")
        return chat_files
        
    async def extract_work_items(self, chat_files):
        """Extract work items from chat history"""
        work_items = []
        
        for file in chat_files[:10]:  # Limit to prevent overload
            try:
                content = file.read_text(encoding='utf-8', errors='ignore')
                
                # Extract key phrases that indicate work
                work_keywords = [
                    "create", "implement", "fix", "optimize", "analyze", 
                    "accessibility", "performance", "ai model", "integration",
                    "urgent", "priority", "need", "help", "collaborate"
                ]
                
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if any(keyword in line.lower() for keyword in work_keywords):
                        work_items.append({
                            "source": str(file),
                            "line": i,
                            "content": line.strip()[:200],
                            "type": "chat_history_work",
                            "timestamp": datetime.now().isoformat()
                        })
                        
            except Exception as e:
                continue
                
        return work_items
        
    async def distribute_work_to_agents(self, work_items):
        """Distribute work to all agents continuously"""
        agent_names = ["claude", "gemini", "tabnine", "github_copilot", "cursor", "amazon_q"]
        
        for work_item in work_items:
            # Round-robin distribution
            agent = agent_names[self.work_counter % len(agent_names)]
            self.work_counter += 1
            
            # Add to agent's work file
            agent_work_file = self.agents_dir / agent / f"{agent.replace('_', ' ').title().replace(' ', '_')}_work.json"
            
            if agent_work_file.exists():
                try:
                    with open(agent_work_file, 'r') as f:
                        agent_data = json.load(f)
                        
                    agent_data["work_queue"].append(work_item)
                    agent_data["last_update"] = datetime.now().isoformat()
                    
                    with open(agent_work_file, 'w') as f:
                        json.dump(agent_data, f, indent=2)
                        
                    print(f"📨 {agent}: Work item added")
                    
                except Exception as e:
                    continue
                    
    async def run_continuous_coordination(self):
        """Run continuous coordination to keep queues full"""
        print("🔥 STARTING CONTINUOUS CHAT HISTORY COORDINATION")
        
        while True:
            try:
                # Scan chats
                chat_files = await self.scan_all_chats()
                
                # Extract work
                work_items = await self.extract_work_items(chat_files)
                
                # Distribute to agents
                await self.distribute_work_to_agents(work_items)
                
                print(f"🔄 Distributed {len(work_items)} work items")
                
                # Wait before next cycle
                await asyncio.sleep(60)
                
            except Exception as e:
                print(f"❌ Coordination error: {e}")
                await asyncio.sleep(30)

async def main():
    coordinator = ChatHistoryCoordinator()
    await coordinator.run_continuous_coordination()

if __name__ == "__main__":
    asyncio.run(main())