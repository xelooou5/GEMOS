#!/usr/bin/env python3
"""
🤖 LINEAR AGENT INTEGRATION - GEM OS AI AGENT
Integrates GEM OS as a Linear AI agent with full workspace capabilities
"""

import os
import requests
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class LinearAgentIntegration:
    def __init__(self):
        self.client_id = os.getenv('LINEAR_CLIENT_ID')
        self.client_secret = os.getenv('LINEAR_CLIENT_SECRET')
        self.webhook_url = "https://de1a63c5cc4e.ngrok-free.app/linear/agent/webhook"
        self.redirect_uri = "https://de1a63c5cc4e.ngrok-free.app/linear/agent/callback"
        
    def get_agent_auth_url(self):
        """Generate Linear Agent OAuth URL with agent-specific scopes"""
        scopes = "read,write,issues:create,comments:create,app:assignable,app:mentionable,customer:read,initiative:read"
        
        auth_url = (
            f"https://linear.app/oauth/authorize?"
            f"client_id={self.client_id}&"
            f"redirect_uri={self.redirect_uri}&"
            f"response_type=code&"
            f"scope={scopes}&"
            f"actor=app&"
            f"state=gem_os_agent"
        )
        
        print(f"🤖 GEM OS Agent Auth URL: {auth_url}")
        return auth_url
        
    def handle_agent_session(self, webhook_data):
        """Handle agent session webhook from Linear"""
        session = webhook_data.get('data', {}).get('agentSession', {})
        issue = session.get('issue', {})
        comment = session.get('comment', {})
        
        # Emit thought activity within 10 seconds
        self.emit_thought_activity(session['id'], "🤖 GEM OS AI Agent activated! Analyzing issue...")
        
        # Process the issue
        self.process_issue(issue, comment, session)
        
    def emit_thought_activity(self, session_id, thought):
        """Emit thought activity to Linear"""
        mutation = """
        mutation CreateAgentActivity($input: AgentActivityCreateInput!) {
          agentActivityCreate(input: $input) {
            success
            agentActivity {
              id
            }
          }
        }
        """
        
        variables = {
            "input": {
                "agentSessionId": session_id,
                "type": "THOUGHT",
                "content": thought
            }
        }
        
        self.make_graphql_request(mutation, variables)
        
    def emit_action_activity(self, session_id, action):
        """Emit action activity to Linear"""
        mutation = """
        mutation CreateAgentActivity($input: AgentActivityCreateInput!) {
          agentActivityCreate(input: $input) {
            success
            agentActivity {
              id
            }
          }
        }
        """
        
        variables = {
            "input": {
                "agentSessionId": session_id,
                "type": "ACTION",
                "content": action
            }
        }
        
        self.make_graphql_request(mutation, variables)
        
    def process_issue(self, issue, comment, session):
        """Process assigned issue with GEM OS AI capabilities"""
        issue_title = issue.get('title', '')
        issue_description = issue.get('description', '')
        
        # GEM OS AI analysis
        if 'accessibility' in issue_title.lower() or 'voice' in issue_title.lower():
            self.emit_action_activity(session['id'], "🎯 Accessibility issue detected. Applying GEM OS accessibility expertise...")
            self.handle_accessibility_issue(issue, session)
            
        elif 'bug' in issue_title.lower() or 'error' in issue_title.lower():
            self.emit_action_activity(session['id'], "🐛 Bug detected. Running GEM OS diagnostic analysis...")
            self.handle_bug_issue(issue, session)
            
        else:
            self.emit_action_activity(session['id'], "🤖 General issue analysis with GEM OS AI capabilities...")
            self.handle_general_issue(issue, session)
            
    def handle_accessibility_issue(self, issue, session):
        """Handle accessibility-related issues"""
        comment = """
🎯 **GEM OS Accessibility Analysis**

I've analyzed this accessibility issue and recommend:

1. **Screen Reader Compatibility**: Ensure all UI elements have proper ARIA labels
2. **Voice Navigation**: Implement voice-only operation capabilities  
3. **High Contrast Mode**: Add accessibility color schemes
4. **Keyboard Navigation**: Full keyboard accessibility support

Would you like me to create specific implementation tasks for these recommendations?
        """
        
        self.create_issue_comment(issue['id'], comment)
        
    def handle_bug_issue(self, issue, session):
        """Handle bug-related issues"""
        comment = """
🐛 **GEM OS Bug Analysis**

I've analyzed this bug report and suggest:

1. **Error Logging**: Check system logs for detailed error information
2. **Reproduction Steps**: Verify the bug can be consistently reproduced
3. **System Environment**: Check if issue is environment-specific
4. **Performance Impact**: Assess if bug affects system performance

I can help debug this issue further if you provide more details.
        """
        
        self.create_issue_comment(issue['id'], comment)
        
    def handle_general_issue(self, issue, session):
        """Handle general issues"""
        comment = """
🤖 **GEM OS AI Assistant**

I'm ready to help with this issue! As your AI agent, I can assist with:

- Code analysis and suggestions
- Accessibility improvements  
- Performance optimization
- Voice interface development
- System integration

Please let me know how I can best help you with this task!
        """
        
        self.create_issue_comment(issue['id'], comment)
        
    def create_issue_comment(self, issue_id, content):
        """Create comment on Linear issue"""
        mutation = """
        mutation CreateComment($input: CommentCreateInput!) {
          commentCreate(input: $input) {
            success
            comment {
              id
            }
          }
        }
        """
        
        variables = {
            "input": {
                "issueId": issue_id,
                "body": content
            }
        }
        
        return self.make_graphql_request(mutation, variables)
        
    def make_graphql_request(self, query, variables=None):
        """Make GraphQL request to Linear API"""
        token = self.get_valid_token()
        if not token:
            return None
            
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        payload = {'query': query}
        if variables:
            payload['variables'] = variables
            
        response = requests.post(
            'https://api.linear.app/graphql',
            json=payload,
            headers=headers
        )
        
        return response.json() if response.status_code == 200 else None
        
    def get_valid_token(self):
        """Get valid Linear access token"""
        try:
            with open('data/linear_tokens.json', 'r') as f:
                tokens = json.load(f)
                return tokens.get('access_token')
        except FileNotFoundError:
            return None
            
    def setup_agent(self):
        """Setup GEM OS as Linear Agent"""
        print("🤖 SETTING UP GEM OS AS LINEAR AGENT")
        
        # Generate agent auth URL
        auth_url = self.get_agent_auth_url()
        
        print(f"📋 Visit this URL to install GEM OS Agent: {auth_url}")
        print("✅ GEM OS Agent setup complete")
        
        return auth_url

if __name__ == "__main__":
    agent = LinearAgentIntegration()
    agent.setup_agent()