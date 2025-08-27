#!/usr/bin/env python3
"""
🔥 GET GEMOS TEAM ID - Fix Linear Integration
"""

import requests
import os
from dotenv import load_dotenv

load_dotenv()

def get_team_id():
    token = os.getenv('CURSOR_LINEAR_TOKEN')
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    query = """
    query {
      teams {
        nodes {
          id
          name
          key
        }
      }
    }
    """
    
    response = requests.post(
        'https://api.linear.app/graphql',
        json={'query': query},
        headers=headers
    )
    
    print(f"Response: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        teams = data.get('data', {}).get('teams', {}).get('nodes', [])
        print("Available teams:")
        for team in teams:
            print(f"  ID: {team['id']}")
            print(f"  Name: {team['name']}")
            print(f"  Key: {team['key']}")
            print()
        return teams[0]['id'] if teams else None
    else:
        print(f"Error: {response.text}")
        return None

if __name__ == "__main__":
    team_id = get_team_id()
    if team_id:
        print(f"✅ Team ID found: {team_id}")
    else:
        print("❌ No team ID found")