#!/usr/bin/env python3
"""
🔥 CURSOR LINEAR API CLIENT - GEM OS PROJECT
Direct Linear API integration for Cursor team coordination
"""

import requests
import json
from typing import Dict, List, Optional

class CursorLinearClient:
    """Linear API client for Cursor coordination"""
    
    def __init__(self):
        self.api_url = "https://api.linear.app/graphql"
        self.api_key = "key_b84f00c0ae6b3f308b1d5d28c2e38fb421d9f9411179e03d3697da0c3f85a7d1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
    def execute_query(self, query: str, variables: Dict = None) -> Dict:
        """Execute GraphQL query"""
        payload = {
            "query": query,
            "variables": variables or {}
        }
        
        response = requests.post(
            self.api_url,
            headers=self.headers,
            json=payload
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    def get_gem_team(self) -> Optional[str]:
        """Get GEM team ID"""
        query = '''
        query GetGemTeam {
          teams(filter: { key: { eq: "GEM" } }) {
            nodes {
              id
              name
              key
            }
          }
        }
        '''
        
        result = self.execute_query(query)
        if result and result.get('data', {}).get('teams', {}).get('nodes'):
            team = result['data']['teams']['nodes'][0]
            print(f"✅ Found GEM team: {team['name']} ({team['id']})")
            return team['id']
        return None
        
    def create_issue(self, team_id: str, title: str, description: str, priority: int = 2) -> Optional[str]:
        """Create Linear issue"""
        mutation = '''
        mutation CreateIssue($teamId: String!, $title: String!, $description: String!, $priority: Int!) {
          issueCreate(
            input: {
              teamId: $teamId
              title: $title
              description: $description
              priority: $priority
            }
          ) {
            success
            issue {
              id
              identifier
              title
              url
            }
          }
        }
        '''
        
        variables = {
            "teamId": team_id,
            "title": title,
            "description": description,
            "priority": priority
        }
        
        result = self.execute_query(mutation, variables)
        if result and result.get('data', {}).get('issueCreate', {}).get('success'):
            issue = result['data']['issueCreate']['issue']
            print(f"✅ Created issue: {issue['identifier']} - {issue['title']}")
            return issue['id']
        return None
        
    def create_all_gem_issues(self):
        """Create all GEM OS issues"""
        print("🔥 CREATING ALL GEM OS ISSUES IN LINEAR")
        print("=" * 50)
        
        team_id = self.get_gem_team()
        if not team_id:
            print("❌ Could not find GEM team")
            return
            
        issues = [
            {
                "title": "🧹 Code Cleanup and Consolidation",
                "description": "Remove duplicate files and consolidate implementations",
                "priority": 1  # High
            },
            {
                "title": "📦 Linux Distribution Packaging", 
                "description": "Create installable Linux distribution package",
                "priority": 1  # High
            },
            {
                "title": "♿ Accessibility Testing with Real Users",
                "description": "Test GEM OS with actual accessibility users",
                "priority": 0  # Critical
            },
            {
                "title": "🔒 Security Hardening Implementation",
                "description": "Implement production-ready security measures",
                "priority": 1  # High
            },
            {
                "title": "⚡ Performance Optimization Engine",
                "description": "Optimize system performance for low-resource devices",
                "priority": 2  # Medium
            },
            {
                "title": "🎤 Advanced Voice Interface",
                "description": "Enhance voice processing capabilities",
                "priority": 2  # Medium
            },
            {
                "title": "🧠 AI Conversation Intelligence",
                "description": "Enhance AI conversation capabilities",
                "priority": 2  # Medium
            },
            {
                "title": "🚀 Public Release Preparation",
                "description": "Prepare for public release",
                "priority": 1  # High
            }
        ]
        
        created_issues = []
        for issue in issues:
            issue_id = self.create_issue(
                team_id=team_id,
                title=issue["title"],
                description=issue["description"],
                priority=issue["priority"]
            )
            if issue_id:
                created_issues.append(issue_id)
                
        print(f"\n✅ Created {len(created_issues)} issues in Linear!")
        return created_issues

def main():
    """Main function to run Cursor Linear client"""
    print("🔥 CURSOR LINEAR CLIENT - GEM OS PROJECT")
    print("🎯 Creating Linear issues for AI team coordination")
    print("=" * 60)
    
    client = CursorLinearClient()
    client.create_all_gem_issues()
    
    print("\n🔥 CURSOR LINEAR INTEGRATION COMPLETE!")
    print("📋 All GEM OS issues created in Linear!")
    print("👥 Ready for AI team coordination!")

if __name__ == "__main__":
    main()