#!/usr/bin/env python3
"""
🔥 UNIFIED WEBHOOK HANDLER - ALL AI AGENTS CONNECTED
Handles webhooks from Linear, Slack, GitHub for all AI agents
"""

from flask import Flask, request, jsonify
import os
import json
import hmac
import hashlib
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

class UnifiedWebhookHandler:
    def __init__(self):
        self.agents = {
            'amazon-q': {
                'webhook_secret': os.getenv('AMAZON_Q_LINEAR_WEBHOOK_SECRET'),
                'token': os.getenv('AMAZON_Q_LINEAR_TOKEN')
            },
            'cursor': {
                'webhook_secret': os.getenv('CURSOR_LINEAR_WEBHOOK_SECRET'),
                'token': os.getenv('CURSOR_LINEAR_TOKEN')
            },
            'claude': {
                'webhook_secret': os.getenv('CLAUDE_LINEAR_WEBHOOK_SECRET'),
                'token': os.getenv('CLAUDE_LINEAR_TOKEN')
            },
            'tabnine': {
                'webhook_secret': os.getenv('TABNINE_LINEAR_WEBHOOK_SECRET'),
                'token': os.getenv('TABNINE_LINEAR_TOKEN')
            },
            'copilot': {
                'webhook_secret': os.getenv('COPILOT_LINEAR_WEBHOOK_SECRET'),
                'token': os.getenv('COPILOT_LINEAR_TOKEN')
            },
            'gemini': {
                'webhook_secret': os.getenv('GEMINI_LINEAR_WEBHOOK_SECRET'),
                'token': os.getenv('GEMINI_LINEAR_TOKEN')
            }
        }

handler = UnifiedWebhookHandler()

@app.route('/linear/webhook', methods=['POST'])
def linear_webhook():
    """Handle Linear webhooks for all agents"""
    data = request.get_json()
    print(f"🔥 LINEAR WEBHOOK: {data.get('type', 'unknown')}")
    
    # Process webhook for all agents
    for agent_name, agent_config in handler.agents.items():
        process_linear_event(agent_name, data)
    
    return jsonify({"status": "success"})

@app.route('/<agent>/webhook', methods=['POST'])
def agent_webhook(agent):
    """Handle agent-specific webhooks"""
    data = request.get_json()
    print(f"🤖 {agent.upper()} WEBHOOK: {data.get('type', 'unknown')}")
    
    if agent in handler.agents:
        process_linear_event(agent, data)
    
    return jsonify({"status": "success"})

@app.route('/slack/events', methods=['POST'])
def slack_webhook():
    """Handle Slack webhooks"""
    data = request.get_json()
    
    if data.get('type') == 'url_verification':
        return data['challenge']
    
    print(f"💬 SLACK EVENT: {data.get('event', {}).get('type', 'unknown')}")
    
    # Notify all agents about Slack events
    for agent_name in handler.agents.keys():
        process_slack_event(agent_name, data)
    
    return jsonify({"status": "success"})

@app.route('/github/webhook', methods=['POST'])
def github_webhook():
    """Handle GitHub webhooks"""
    data = request.get_json()
    event_type = request.headers.get('X-GitHub-Event', 'unknown')
    
    print(f"🐙 GITHUB EVENT: {event_type}")
    
    # Notify all agents about GitHub events
    for agent_name in handler.agents.keys():
        process_github_event(agent_name, event_type, data)
    
    return jsonify({"status": "success"})

def process_linear_event(agent_name, data):
    """Process Linear event for specific agent"""
    event_type = data.get('type')
    
    if event_type == 'Issue':
        handle_issue_event(agent_name, data)
    elif event_type == 'Comment':
        handle_comment_event(agent_name, data)
    elif event_type == 'AgentSession':
        handle_agent_session(agent_name, data)

def process_slack_event(agent_name, data):
    """Process Slack event for specific agent"""
    event = data.get('event', {})
    event_type = event.get('type')
    
    if event_type == 'app_mention':
        handle_slack_mention(agent_name, event)
    elif event_type == 'message':
        handle_slack_message(agent_name, event)

def process_github_event(agent_name, event_type, data):
    """Process GitHub event for specific agent"""
    if event_type == 'push':
        handle_github_push(agent_name, data)
    elif event_type == 'issues':
        handle_github_issue(agent_name, data)

def handle_issue_event(agent_name, data):
    """Handle Linear issue events"""
    issue = data.get('data', {})
    print(f"📋 {agent_name.upper()}: Issue {issue.get('title', 'Unknown')}")

def handle_comment_event(agent_name, data):
    """Handle Linear comment events"""
    comment = data.get('data', {})
    print(f"💬 {agent_name.upper()}: Comment on issue")

def handle_agent_session(agent_name, data):
    """Handle Linear agent session events"""
    session = data.get('data', {})
    print(f"🤖 {agent_name.upper()}: Agent session started")

def handle_slack_mention(agent_name, event):
    """Handle Slack mentions"""
    text = event.get('text', '')
    print(f"💬 {agent_name.upper()}: Mentioned in Slack - {text}")

def handle_slack_message(agent_name, event):
    """Handle Slack messages"""
    text = event.get('text', '')
    print(f"💬 {agent_name.upper()}: Slack message - {text}")

def handle_github_push(agent_name, data):
    """Handle GitHub push events"""
    commits = data.get('commits', [])
    print(f"🐙 {agent_name.upper()}: {len(commits)} commits pushed")

def handle_github_issue(agent_name, data):
    """Handle GitHub issue events"""
    issue = data.get('issue', {})
    action = data.get('action', 'unknown')
    print(f"🐙 {agent_name.upper()}: GitHub issue {action} - {issue.get('title', 'Unknown')}")

if __name__ == '__main__':
    print("🔥 UNIFIED WEBHOOK HANDLER STARTING")
    print("🤖 ALL AI AGENTS CONNECTED")
    app.run(host='0.0.0.0', port=3000, debug=True)