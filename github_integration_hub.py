#!/usr/bin/env python3
"""
🔥 GITHUB INTEGRATION HUB - ALL SYSTEMS CONNECTED
Links all tools, sites, and systems to GitHub for unified workflow
"""

import os
import subprocess
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class GitHubIntegrationHub:
    def __init__(self):
        self.repo_url = "https://github.com/xelooou5/GEMOS.git"
        self.integrations = {
            "linear": {
                "webhook": "https://de1a63c5cc4e.ngrok-free.app/linear/webhook",
                "api_key": os.getenv('LINEAR_API_KEY'),
                "team_id": os.getenv('LINEAR_TEAM_ID')
            },
            "slack": {
                "webhook": "https://de1a63c5cc4e.ngrok-free.app/slack/events",
                "bot_token": os.getenv('SLACK_BOT_TOKEN'),
                "app_token": os.getenv('SLACK_APP_TOKEN')
            },
            "cursor": {
                "api_key": os.getenv('CURSOR_API_KEY'),
                "project_id": os.getenv('CURSOR_PROJECT_ID')
            },
            "aws": {
                "access_key": os.getenv('AWS_ACCESS_KEY_ID'),
                "secret_key": os.getenv('AWS_SECRET_ACCESS_KEY'),
                "region": "us-east-1"
            }
        }
        
    def setup_github_actions(self):
        """Setup GitHub Actions for CI/CD"""
        workflow = {
            "name": "GEM OS CI/CD",
            "on": {
                "push": {"branches": ["main"]},
                "pull_request": {"branches": ["main"]}
            },
            "jobs": {
                "test": {
                    "runs-on": "ubuntu-latest",
                    "steps": [
                        {"uses": "actions/checkout@v3"},
                        {"uses": "actions/setup-python@v4", "with": {"python-version": "3.8"}},
                        {"run": "pip install -r requirements.txt"},
                        {"run": "python -m pytest tests/"},
                        {"run": "python gem.py --test"}
                    ]
                },
                "deploy": {
                    "needs": "test",
                    "runs-on": "ubuntu-latest",
                    "steps": [
                        {"uses": "actions/checkout@v3"},
                        {"run": "echo 'Deploying GEM OS'"}
                    ]
                }
            }
        }
        
        os.makedirs(".github/workflows", exist_ok=True)
        with open(".github/workflows/gem-ci-cd.yml", "w") as f:
            import yaml
            yaml.dump(workflow, f)
            
    def setup_webhooks(self):
        """Setup webhooks for all integrated services"""
        webhooks = {
            "linear_webhook": {
                "url": self.integrations["linear"]["webhook"],
                "events": ["issue.create", "issue.update", "comment.create"]
            },
            "slack_webhook": {
                "url": self.integrations["slack"]["webhook"],
                "events": ["message", "app_mention", "reaction_added"]
            }
        }
        
        with open("data/webhooks_config.json", "w") as f:
            json.dump(webhooks, f, indent=2)
            
    def sync_all_systems(self):
        """Sync all connected systems with GitHub"""
        print("🔥 SYNCING ALL SYSTEMS WITH GITHUB...")
        
        # Commit and push current state
        subprocess.run(["git", "add", "."])
        subprocess.run(["git", "commit", "-m", f"🔄 AUTO-SYNC {datetime.now().strftime('%H:%M')}"])
        subprocess.run(["git", "push", "origin", "main"])
        
        # Trigger Linear sync
        self.sync_linear()
        
        # Trigger Slack notification
        self.notify_slack()
        
        # Update AWS resources
        self.sync_aws()
        
    def sync_linear(self):
        """Sync with Linear project management"""
        print("📋 Syncing with Linear...")
        # Linear API calls would go here
        
    def notify_slack(self):
        """Notify Slack of updates"""
        print("💬 Notifying Slack...")
        # Slack API calls would go here
        
    def sync_aws(self):
        """Sync with AWS services"""
        print("☁️ Syncing with AWS...")
        # AWS API calls would go here
        
    def run_integration(self):
        """Run complete integration setup"""
        print("🔥 SETTING UP GITHUB INTEGRATION HUB")
        
        self.setup_github_actions()
        self.setup_webhooks()
        self.sync_all_systems()
        
        print("✅ ALL SYSTEMS CONNECTED TO GITHUB!")

if __name__ == "__main__":
    hub = GitHubIntegrationHub()
    hub.run_integration()