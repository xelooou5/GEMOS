#!/usr/bin/env python3
"""
🔥 LINEAR OAUTH DAEMON - NEVER FORGET INTEGRATION
Handles Linear OAuth2 authentication and token management
"""

import os
import requests
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

class LinearOAuthDaemon:
    def __init__(self):
        self.client_id = os.getenv('LINEAR_CLIENT_ID')
        self.client_secret = os.getenv('LINEAR_CLIENT_SECRET')
        self.redirect_uri = "https://de1a63c5cc4e.ngrok-free.app/linear/callback"
        self.token_file = "data/linear_tokens.json"
        
    def get_auth_url(self):
        """Generate Linear OAuth authorization URL"""
        scopes = "read,write,issues:create,comments:create"
        state = "gem_os_integration"
        
        auth_url = (
            f"https://linear.app/oauth/authorize?"
            f"client_id={self.client_id}&"
            f"redirect_uri={self.redirect_uri}&"
            f"response_type=code&"
            f"scope={scopes}&"
            f"state={state}&"
            f"actor=app"
        )
        
        print(f"🔗 Linear Auth URL: {auth_url}")
        return auth_url
        
    def exchange_code_for_token(self, code):
        """Exchange authorization code for access token"""
        data = {
            'code': code,
            'redirect_uri': self.redirect_uri,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'authorization_code'
        }
        
        response = requests.post(
            'https://api.linear.app/oauth/token',
            data=data,
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )
        
        if response.status_code == 200:
            tokens = response.json()
            self.save_tokens(tokens)
            print("✅ Linear tokens saved")
            return tokens
        else:
            print(f"❌ Token exchange failed: {response.text}")
            return None
            
    def refresh_token(self):
        """Refresh expired access token"""
        tokens = self.load_tokens()
        if not tokens or 'refresh_token' not in tokens:
            return None
            
        data = {
            'refresh_token': tokens['refresh_token'],
            'grant_type': 'refresh_token'
        }
        
        response = requests.post(
            'https://api.linear.app/oauth/token',
            data=data,
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )
        
        if response.status_code == 200:
            new_tokens = response.json()
            self.save_tokens(new_tokens)
            print("✅ Linear tokens refreshed")
            return new_tokens
        else:
            print(f"❌ Token refresh failed: {response.text}")
            return None
            
    def save_tokens(self, tokens):
        """Save tokens to file"""
        os.makedirs("data", exist_ok=True)
        tokens['expires_at'] = (datetime.now() + timedelta(seconds=tokens['expires_in'])).isoformat()
        
        with open(self.token_file, 'w') as f:
            json.dump(tokens, f, indent=2)
            
    def load_tokens(self):
        """Load tokens from file"""
        try:
            with open(self.token_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return None
            
    def get_valid_token(self):
        """Get valid access token, refreshing if needed"""
        tokens = self.load_tokens()
        if not tokens:
            return None
            
        # Check if token is expired
        expires_at = datetime.fromisoformat(tokens['expires_at'])
        if datetime.now() >= expires_at:
            tokens = self.refresh_token()
            
        return tokens['access_token'] if tokens else None
        
    def make_api_request(self, query):
        """Make GraphQL request to Linear API"""
        token = self.get_valid_token()
        if not token:
            print("❌ No valid Linear token")
            return None
            
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        response = requests.post(
            'https://api.linear.app/graphql',
            json={'query': query},
            headers=headers
        )
        
        return response.json() if response.status_code == 200 else None
        
    def sync_with_github(self):
        """Sync Linear issues with GitHub"""
        query = """
        {
          issues(first: 10) {
            nodes {
              id
              title
              description
              state {
                name
              }
            }
          }
        }
        """
        
        result = self.make_api_request(query)
        if result:
            print("✅ Linear sync successful")
            return result
        else:
            print("❌ Linear sync failed")
            return None
            
    def run_daemon(self):
        """Run Linear OAuth daemon"""
        print("🔥 LINEAR OAUTH DAEMON ACTIVE")
        
        # Generate auth URL if no tokens
        if not self.load_tokens():
            auth_url = self.get_auth_url()
            print(f"📋 Visit: {auth_url}")
        
        # Sync with GitHub
        self.sync_with_github()
        
        print("✅ Linear OAuth daemon complete")

if __name__ == "__main__":
    daemon = LinearOAuthDaemon()
    daemon.run_daemon()