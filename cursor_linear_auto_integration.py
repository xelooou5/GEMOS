#!/usr/bin/env python3
"""
🎯 CURSOR LINEAR AUTO INTEGRATION - CREATE ISSUES AUTOMATICALLY
Cursor creates Linear issues for team cross-help and fixes
"""

import requests
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class CursorLinearIntegration:
    def __init__(self):
        self.token = os.getenv('CURSOR_LINEAR_TOKEN')
        self.workspace = "gemos"
        
    def create_team_issues(self):
        """🎯 CURSOR: Create Linear issues for all AI agents"""
        print("🎯 CURSOR CREATING LINEAR ISSUES FOR TEAM")
        
        issues = [
            {
                "title": "🎤 COPILOT: Fix PyAudio Import Error - LISTEN Pillar",
                "description": "**ASSIGNED TO:** Copilot\n**CROSS-HELP FROM:** Cursor, Amazon Q\n\n**ISSUE:** PyAudio import failing, blocking voice input\n\n**TASKS:**\n- [ ] Fix PyAudio installation path\n- [ ] Test microphone detection\n- [ ] Implement wake word system\n- [ ] Cross-help: Cursor will test voice commands\n\n**PRIORITY:** CRITICAL",
                "assignee": "copilot",
                "labels": ["critical", "listen-pillar", "cross-help"]
            },
            {
                "title": "🗣️ GEMINI: Optimize TTS Voice Quality - TALK Pillar", 
                "description": "**ASSIGNED TO:** Gemini\n**CROSS-HELP FROM:** Claude, Cursor\n\n**ISSUE:** TTS voice needs accessibility optimization\n\n**TASKS:**\n- [ ] Implement beautiful voice selection\n- [ ] Test multilingual speech\n- [ ] Cross-help: Claude will test accessibility\n- [ ] Cross-help: Cursor will test voice commands\n\n**PRIORITY:** HIGH",
                "assignee": "gemini",
                "labels": ["high", "talk-pillar", "accessibility"]
            },
            {
                "title": "🧠 TABNINE: Complete Memory Database Integration - LEARN_MEMORIZE",
                "description": "**ASSIGNED TO:** TabNine\n**CROSS-HELP FROM:** Amazon Q, Cursor\n\n**ISSUE:** Memory system needs database integration\n\n**TASKS:**\n- [ ] Fix memory database connection\n- [ ] Implement conversation storage\n- [ ] Cross-help: Amazon Q will coordinate\n- [ ] Cross-help: Cursor will test memory commands\n\n**PRIORITY:** HIGH",
                "assignee": "tabnine", 
                "labels": ["high", "memory-pillar", "database"]
            },
            {
                "title": "♿ CLAUDE: Screen Reader Integration Testing - ACCESSIBILITY",
                "description": "**ASSIGNED TO:** Claude\n**CROSS-HELP FROM:** All agents\n\n**ISSUE:** Need real screen reader testing\n\n**TASKS:**\n- [ ] Test with NVDA/Orca screen readers\n- [ ] Implement voice-only mode\n- [ ] Cross-help: All agents test accessibility\n- [ ] Emergency accessibility mode\n\n**PRIORITY:** CRITICAL",
                "assignee": "claude",
                "labels": ["critical", "accessibility", "screen-reader"]
            },
            {
                "title": "🎯 CURSOR: Voice-to-Action Pipeline - TAKE_ACTION Pillar",
                "description": "**ASSIGNED TO:** Cursor\n**CROSS-HELP FROM:** Copilot, Gemini\n\n**ISSUE:** Connect voice commands to Linear actions\n\n**TASKS:**\n- [ ] Build voice-to-action pipeline\n- [ ] Create Linear tasks from voice\n- [ ] Cross-help: Copilot provides voice input\n- [ ] Cross-help: Gemini provides voice feedback\n\n**PRIORITY:** HIGH",
                "assignee": "cursor",
                "labels": ["high", "action-pillar", "voice-commands"]
            }
        ]
        
        for issue in issues:
            self.create_linear_issue(issue)
            
    def create_linear_issue(self, issue_data):
        """Create Linear issue with cross-help assignments"""
        headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }
        
        mutation = """
        mutation IssueCreate($input: IssueCreateInput!) {
          issueCreate(input: $input) {
            success
            issue {
              id
              title
              url
            }
          }
        }
        """
        
        variables = {
            "input": {
                "title": issue_data["title"],
                "description": issue_data["description"]
            }
        }
        
        try:
            response = requests.post(
                'https://api.linear.app/graphql',
                json={'query': mutation, 'variables': variables},
                headers=headers
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('data', {}).get('issueCreate', {}).get('success'):
                    issue = result['data']['issueCreate']['issue']
                    print(f"✅ Created: {issue['title']}")
                    print(f"   URL: {issue['url']}")
                    return issue
                else:
                    print(f"❌ Failed: {issue_data['title']}")
                    print(f"   Error: {result}")
            else:
                print(f"❌ API Error {response.status_code}: {response.text}")
                
        except Exception as e:
            print(f"❌ Exception: {e}")
            
        return None
        
    def setup_cross_help_system(self):
        """🎯 CURSOR: Setup cross-help between all agents"""
        print("🤝 CURSOR SETTING UP CROSS-HELP SYSTEM")
        
        cross_help_plan = {
            "copilot_helps": ["gemini", "cursor"],  # Voice input helps speech and actions
            "gemini_helps": ["copilot", "claude"],  # Speech helps voice and accessibility  
            "cursor_helps": ["all"],  # Actions help everyone
            "tabnine_helps": ["all"],  # Memory helps everyone
            "claude_helps": ["all"],  # Accessibility helps everyone
            "amazon_q_coordinates": ["all"]  # Brain coordinates all
        }
        
        print("🤝 Cross-help assignments:")
        for helper, helps in cross_help_plan.items():
            print(f"   {helper} → {helps}")
            
        return cross_help_plan

if __name__ == "__main__":
    cursor = CursorLinearIntegration()
    cursor.create_team_issues()
    cursor.setup_cross_help_system()