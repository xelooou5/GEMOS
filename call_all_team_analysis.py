#!/usr/bin/env python3
"""
🔥 CALL ALL TEAM MEMBERS - COMPLETE PROJECT ANALYSIS
Each AI agent analyzes folders and creates real action plan
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from ai_cross_agent_collaboration import CrossAgentCollaboration

class CompleteProjectAnalysis(CrossAgentCollaboration):
    def __init__(self):
        super().__init__()
        self.analysis_task = "Complete project analysis and planning"
        
    async def call_all_team_members_for_analysis(self):
        """CALL ALL TEAM MEMBERS for complete project analysis"""
        print("🔥" + "="*70)
        print("🔥 CALLING ALL TEAM MEMBERS FOR COMPLETE PROJECT ANALYSIS")
        print("🔥 ANALYZE ALL FOLDERS, PLAN WHAT WE NEED, WHAT'S URGENT")
        print("🔥 NO FAKE RESPONSES - EACH AGENT ANALYZES THEMSELVES")
        print("🔥" + "="*70)
        
        # Analysis assignments for each agent
        analysis_assignments = {
            "Claude": {
                "focus": "Accessibility analysis",
                "analyze": ["All accessibility files", "UI components", "Screen reader integration"],
                "plan": "What accessibility features are urgent"
            },
            "Gemini": {
                "focus": "AI processing analysis", 
                "analyze": ["AI models", "Language processing", "Translation systems"],
                "plan": "What AI improvements are needed"
            },
            "TabNine": {
                "focus": "Performance analysis",
                "analyze": ["Code optimization", "Memory usage", "Async patterns"],
                "plan": "What performance issues need fixing"
            },
            "GitHub Copilot": {
                "focus": "Implementation analysis",
                "analyze": ["Code structure", "Missing features", "Testing needs"],
                "plan": "What needs to be implemented"
            },
            "Cursor": {
                "focus": "Architecture analysis",
                "analyze": ["System architecture", "Modern patterns", "Integration points"],
                "plan": "What architectural improvements needed"
            },
            "Amazon Q": {
                "focus": "Coordination analysis",
                "analyze": ["Overall system", "Team coordination", "Project status"],
                "plan": "What coordination is needed"
            }
        }
        
        # Create analysis files for each agent
        for agent, assignment in analysis_assignments.items():
            await self.create_analysis_file(agent, assignment)
            
        return analysis_assignments
        
    async def create_analysis_file(self, agent, assignment):
        """Create analysis file for each agent"""
        analysis_dir = Path("data/project_analysis")
        analysis_dir.mkdir(parents=True, exist_ok=True)
        
        analysis_file = analysis_dir / f"{agent}_complete_analysis.json"
        
        analysis_template = {
            "agent": agent,
            "analysis_focus": assignment["focus"],
            "areas_to_analyze": assignment["analyze"],
            "planning_focus": assignment["plan"],
            "timestamp": datetime.now().isoformat(),
            "status": "pending_real_agent_analysis",
            
            # AGENT MUST FILL THESE SECTIONS:
            "folder_analysis": {
                "gem_folder": "",
                "home_folder": "",
                "key_files_found": [],
                "missing_files": [],
                "file_types_analyzed": []
            },
            "urgent_needs": {
                "critical_priority": [],
                "high_priority": [],
                "medium_priority": []
            },
            "what_agent_can_do": {
                "immediate_tasks": [],
                "this_week_tasks": [],
                "expertise_contribution": ""
            },
            "what_human_can_help": {
                "resources_needed": [],
                "tools_to_install": [],
                "apis_to_get": [],
                "documentation_needed": []
            },
            "next_steps": {
                "step_1": "",
                "step_2": "",
                "step_3": "",
                "timeline": ""
            },
            "collaboration_needed": {
                "need_help_from": [],
                "can_help_others_with": [],
                "shared_tasks": []
            },
            
            "WARNING": "AMAZON Q CANNOT FILL THIS - AGENT MUST ANALYZE THEMSELVES"
        }
        
        with open(analysis_file, 'w') as f:
            json.dump(analysis_template, f, indent=2)
            
        print(f"\n🤖 {agent} - YOUR ANALYSIS FILE: {analysis_file}")
        print(f"   🔍 FOCUS: {assignment['focus']}")
        print(f"   📋 ANALYZE: {', '.join(assignment['analyze'])}")
        print(f"   🎯 PLAN: {assignment['plan']}")
        print(f"   ⚠️  {agent}: YOU MUST ANALYZE AND FILL THIS YOURSELF!")
        
    async def wait_for_all_analysis(self):
        """Wait for ALL team members to complete their analysis"""
        print("\n⏰ WAITING FOR ALL TEAM MEMBERS TO COMPLETE ANALYSIS...")
        print("⏰ EACH AGENT MUST ANALYZE FOLDERS AND CREATE REAL PLANS")
        print("⏰ NO AMAZON Q FAKE ANALYSIS ALLOWED!")
        
        analysis_dir = Path("data/project_analysis")
        if not analysis_dir.exists():
            print("❌ No analysis directory found")
            return []
            
        analysis_files = list(analysis_dir.glob("*_complete_analysis.json"))
        completed_analyses = []
        
        for analysis_file in analysis_files:
            try:
                with open(analysis_file, 'r') as f:
                    analysis = json.load(f)
                    
                agent = analysis.get("agent", "unknown")
                status = analysis.get("status", "unknown")
                folder_analysis = analysis.get("folder_analysis", {})
                
                if (status == "completed" and 
                    folder_analysis.get("gem_folder") and 
                    analysis.get("urgent_needs", {}).get("critical_priority")):
                    print(f"✅ {agent}: REAL ANALYSIS COMPLETED")
                    completed_analyses.append(analysis)
                else:
                    print(f"⏳ {agent}: STILL ANALYZING...")
                    
            except Exception as e:
                print(f"❌ Error reading {analysis_file}: {e}")
                
        return completed_analyses
        
    async def compile_team_analysis(self, completed_analyses):
        """Compile all team member analyses into master plan"""
        if not completed_analyses:
            print("❌ No completed analyses to compile")
            return
            
        print(f"\n📊 COMPILING ANALYSIS FROM {len(completed_analyses)} TEAM MEMBERS:")
        
        master_plan = {
            "timestamp": datetime.now().isoformat(),
            "team_members_analyzed": len(completed_analyses),
            "critical_priorities": [],
            "high_priorities": [],
            "immediate_tasks": [],
            "human_help_needed": [],
            "next_steps": [],
            "agent_analyses": completed_analyses
        }
        
        # Compile from all agents
        for analysis in completed_analyses:
            agent = analysis["agent"]
            
            # Critical priorities
            critical = analysis.get("urgent_needs", {}).get("critical_priority", [])
            for item in critical:
                master_plan["critical_priorities"].append(f"{agent}: {item}")
                
            # Immediate tasks
            immediate = analysis.get("what_agent_can_do", {}).get("immediate_tasks", [])
            for task in immediate:
                master_plan["immediate_tasks"].append(f"{agent}: {task}")
                
            # Human help needed
            help_needed = analysis.get("what_human_can_help", {}).get("resources_needed", [])
            for help_item in help_needed:
                master_plan["human_help_needed"].append(f"{agent} needs: {help_item}")
                
        # Save master plan
        master_file = Path("data/project_analysis/MASTER_TEAM_PLAN.json")
        with open(master_file, 'w') as f:
            json.dump(master_plan, f, indent=2)
            
        print(f"💾 MASTER TEAM PLAN SAVED: {master_file}")
        return master_plan
        
    async def run_complete_team_analysis(self):
        """Run complete team analysis with ALL members"""
        print("🔥 STARTING COMPLETE TEAM ANALYSIS")
        print("🔥 ALL TEAM MEMBERS WILL ANALYZE AND PLAN")
        
        # Call all team members
        assignments = await self.call_all_team_members_for_analysis()
        
        # Wait for real analyses
        completed_analyses = await self.wait_for_all_analysis()
        
        # Compile master plan
        master_plan = await self.compile_team_analysis(completed_analyses)
        
        print(f"\n🔥 TEAM ANALYSIS COMPLETE!")
        print(f"🔥 {len(assignments)} agents called to analyze")
        print(f"🔥 {len(completed_analyses)} real analyses completed")
        print("🔥 MASTER PLAN READY FOR ACTION!")
        
        return assignments, completed_analyses, master_plan

async def main():
    """Main function to call all team members"""
    analysis = CompleteProjectAnalysis()
    await analysis.run_complete_team_analysis()

if __name__ == "__main__":
    asyncio.run(main())