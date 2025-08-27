#!/usr/bin/env python3
"""
🔥 QUICK LINEAR TEST - CREATE ISSUES NOW
"""

import requests
import os
from dotenv import load_dotenv

load_dotenv()

def create_linear_issue():
    token = os.getenv('AMAZON_Q_LINEAR_TOKEN')
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    # Get team ID first
    team_query = """
    query {
      teams {
        nodes {
          id
          name
        }
      }
    }
    """
    
    response = requests.post(
        'https://api.linear.app/graphql',
        json={'query': team_query},
        headers=headers
    )
    
    print(f"Team query response: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 200:
        data = response.json()
        teams = data.get('data', {}).get('teams', {}).get('nodes', [])
        if teams:
            team_id = teams[0]['id']
            print(f"✅ Found team ID: {team_id}")
            
            # Create issue
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
                    "title": "🔥 AI TEAM TEST ISSUE",
                    "description": "Test issue created by AI team",
                    "teamId": team_id
                }
            }
            
            issue_response = requests.post(
                'https://api.linear.app/graphql',
                json={'query': mutation, 'variables': variables},
                headers=headers
            )
            
            print(f"Issue creation response: {issue_response.status_code}")
            print(f"Response: {issue_response.text}")
        else:
            print("❌ No teams found")
    else:
        print(f"❌ Team query failed: {response.status_code}")

if __name__ == "__main__":
    create_linear_issue()