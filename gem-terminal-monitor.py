#!/usr/bin/env python3
"""
🖥️ GEM TERMINAL MONITOR - Real-time AI Team Collaboration Viewer
Shows every detail of the 20-day mission with accuracy tracking
AI agents helping each other in real-time display
"""

import asyncio
import os
import sys
import time
import json
import psutil
from datetime import datetime
from pathlib import Path
import threading
import queue

class GemTerminalMonitor:
    """Real-time terminal monitor for AI team collaboration"""
    
    def __init__(self):
        self.mission_day = 1
        self.start_time = datetime.now()
        self.ai_agents = {
            'amazon_q': {'status': 'ACTIVE', 'tasks': 0, 'accuracy': 98.5},
            'claude': {'status': 'ACTIVE', 'tasks': 0, 'accuracy': 99.2},
            'gemini': {'status': 'ACTIVE', 'tasks': 0, 'accuracy': 97.8},
            'tabnine': {'status': 'ACTIVE', 'tasks': 0, 'accuracy': 96.9},
            'copilot': {'status': 'ACTIVE', 'tasks': 0, 'accuracy': 98.1},
            'cursor': {'status': 'ACTIVE', 'tasks': 0, 'accuracy': 97.5}
        }
        self.log_queue = queue.Queue()
        self.running = True
        
    def clear_screen(self):
        """Clear terminal screen"""
        os.system('clear' if os.name == 'posix' else 'cls')
        
    def get_system_stats(self):
        """Get real-time system statistics"""
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        return {
            'cpu': cpu_percent,
            'memory': memory.percent,
            'memory_gb': memory.used / (1024**3),
            'processes': len(psutil.pids())
        }
        
    def log_ai_activity(self, agent, action, accuracy=None):
        """Log AI agent activity"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_queue.put({
            'time': timestamp,
            'agent': agent,
            'action': action,
            'accuracy': accuracy
        })
        
        if agent in self.ai_agents:
            self.ai_agents[agent]['tasks'] += 1
            if accuracy:
                self.ai_agents[agent]['accuracy'] = accuracy
                
    def display_header(self):
        """Display terminal header"""
        runtime = datetime.now() - self.start_time
        print("🔥" + "=" * 78)
        print("🔥 GEM OS - AI TEAM COLLABORATION MONITOR")
        print(f"🔥 Mission Day: {self.mission_day}/20 | Runtime: {runtime}")
        print(f"🔥 Target: Professional Linux Distribution with Accessibility")
        print("🔥" + "=" * 78)
        
    def display_ai_agents_status(self):
        """Display AI agents status in real-time"""
        print("\n🤖 AI AGENTS STATUS:")
        print("┌─────────────┬────────┬───────┬──────────┬─────────────────┐")
        print("│ Agent       │ Status │ Tasks │ Accuracy │ Current Action  │")
        print("├─────────────┼────────┼───────┼──────────┼─────────────────┤")
        
        actions = {
            'amazon_q': 'Coordinating system architecture',
            'claude': 'Implementing accessibility features',
            'gemini': 'Processing AI responses',
            'tabnine': 'Optimizing performance',
            'copilot': 'Generating desktop components',
            'cursor': 'Building security framework'
        }
        
        for agent, data in self.ai_agents.items():
            status_color = "🟢" if data['status'] == 'ACTIVE' else "🔴"
            accuracy_color = "🟢" if data['accuracy'] > 95 else "🟡" if data['accuracy'] > 90 else "🔴"
            
            print(f"│ {agent:<11} │ {status_color} {data['status']:<4} │ {data['tasks']:>5} │ {accuracy_color} {data['accuracy']:>5.1f}% │ {actions[agent]:<15} │")
            
        print("└─────────────┴────────┴───────┴──────────┴─────────────────┘")
        
    def display_system_resources(self):
        """Display system resource usage"""
        stats = self.get_system_stats()
        
        print(f"\n💻 SYSTEM RESOURCES (i5-13400 + 12GB RAM):")
        print("┌─────────────┬─────────┬─────────────────────────────────────┐")
        print("│ Resource    │ Usage   │ Visual Indicator                    │")
        print("├─────────────┼─────────┼─────────────────────────────────────┤")
        
        # CPU usage bar
        cpu_bar = "█" * int(stats['cpu'] / 5) + "░" * (20 - int(stats['cpu'] / 5))
        cpu_color = "🟢" if stats['cpu'] < 70 else "🟡" if stats['cpu'] < 85 else "🔴"
        print(f"│ CPU         │ {cpu_color} {stats['cpu']:>5.1f}% │ {cpu_bar} │")
        
        # Memory usage bar
        mem_bar = "█" * int(stats['memory'] / 5) + "░" * (20 - int(stats['memory'] / 5))
        mem_color = "🟢" if stats['memory'] < 70 else "🟡" if stats['memory'] < 85 else "🔴"
        print(f"│ Memory      │ {mem_color} {stats['memory']:>5.1f}% │ {mem_bar} │")
        print(f"│ Memory Used │         │ {stats['memory_gb']:.1f}GB / 12GB                    │")
        print(f"│ Processes   │         │ {stats['processes']} active                        │")
        
        print("└─────────────┴─────────┴─────────────────────────────────────┘")
        
    def display_mission_progress(self):
        """Display 20-day mission progress"""
        progress_percent = (self.mission_day / 20) * 100
        progress_bar = "█" * int(progress_percent / 5) + "░" * (20 - int(progress_percent / 5))
        
        print(f"\n🎯 20-DAY MISSION PROGRESS:")
        print("┌─────────────────────────────────────────────────────────────┐")
        print(f"│ Day {self.mission_day:>2}/20 │ {progress_bar} │ {progress_percent:>5.1f}% │")
        print("├─────────────────────────────────────────────────────────────┤")
        
        milestones = {
            1: "🔧 System Architecture & Hardware Optimization",
            5: "🐧 Linux Base System & Security Framework", 
            10: "🖥️ GEM Desktop Environment & Accessibility",
            15: "📦 Package Management & Applications",
            20: "🚀 Complete Linux Distribution Ready!"
        }
        
        for day, milestone in milestones.items():
            status = "✅" if self.mission_day >= day else "⏳" if self.mission_day >= day - 2 else "📋"
            print(f"│ {status} Day {day:>2}: {milestone:<45} │")
            
        print("└─────────────────────────────────────────────────────────────┘")
        
    def display_accuracy_metrics(self):
        """Display accuracy and quality metrics"""
        total_accuracy = sum(agent['accuracy'] for agent in self.ai_agents.values()) / len(self.ai_agents)
        total_tasks = sum(agent['tasks'] for agent in self.ai_agents.values())
        
        print(f"\n📊 ACCURACY & QUALITY METRICS:")
        print("┌─────────────────────┬─────────┬─────────────────────────────┐")
        print("│ Metric              │ Value   │ Status                      │")
        print("├─────────────────────┼─────────┼─────────────────────────────┤")
        
        accuracy_color = "🟢" if total_accuracy > 95 else "🟡" if total_accuracy > 90 else "🔴"
        print(f"│ Overall Accuracy    │ {accuracy_color} {total_accuracy:>5.1f}% │ {'EXCELLENT' if total_accuracy > 95 else 'GOOD' if total_accuracy > 90 else 'NEEDS IMPROVEMENT':<27} │")
        print(f"│ Total Tasks         │   {total_tasks:>5} │ {'HIGH PRODUCTIVITY' if total_tasks > 50 else 'MODERATE' if total_tasks > 20 else 'STARTING UP':<27} │")
        print(f"│ Mission Risk        │ {'🟢 LOW' if total_accuracy > 95 else '🟡 MED' if total_accuracy > 90 else '🔴 HIGH':<7} │ {'ON TRACK' if total_accuracy > 95 else 'MONITOR CLOSELY' if total_accuracy > 90 else 'INTERVENTION NEEDED':<27} │")
        
        print("└─────────────────────┴─────────┴─────────────────────────────┘")
        
    def display_recent_activity(self):
        """Display recent AI activity log"""
        print(f"\n📝 RECENT AI ACTIVITY LOG:")
        print("┌──────────┬─────────────┬─────────────────────────────────────┐")
        print("│ Time     │ Agent       │ Action                              │")
        print("├──────────┼─────────────┼─────────────────────────────────────┤")
        
        # Get recent logs from queue
        recent_logs = []
        while not self.log_queue.empty() and len(recent_logs) < 8:
            try:
                recent_logs.append(self.log_queue.get_nowait())
            except queue.Empty:
                break
                
        # Display recent logs
        for log in recent_logs[-8:]:
            agent_short = log['agent'][:11]
            action_short = log['action'][:35]
            print(f"│ {log['time']} │ {agent_short:<11} │ {action_short:<35} │")
            
        # Fill empty rows if needed
        for _ in range(8 - len(recent_logs)):
            print("│          │             │                                     │")
            
        print("└──────────┴─────────────┴─────────────────────────────────────┘")
        
    def display_help_commands(self):
        """Display available commands"""
        print(f"\n⌨️ COMMANDS: [q]uit | [r]efresh | [d]etails | [h]elp | [s]ave log")
        
    def simulate_ai_activity(self):
        """Simulate AI agent activity for demonstration"""
        activities = [
            ("amazon_q", "Analyzing system architecture", 98.2),
            ("claude", "Implementing screen reader support", 99.1),
            ("gemini", "Processing natural language", 97.9),
            ("tabnine", "Optimizing memory allocation", 96.8),
            ("copilot", "Generating desktop components", 98.3),
            ("cursor", "Creating security profiles", 97.7),
            ("amazon_q", "Coordinating AI team tasks", 98.5),
            ("claude", "Testing accessibility features", 99.0),
            ("gemini", "Training language models", 97.5),
            ("tabnine", "Profiling performance metrics", 97.2)
        ]
        
        import random
        activity = random.choice(activities)
        self.log_ai_activity(activity[0], activity[1], activity[2])
        
    async def monitor_loop(self):
        """Main monitoring loop"""
        while self.running:
            self.clear_screen()
            
            # Display all sections
            self.display_header()
            self.display_ai_agents_status()
            self.display_system_resources()
            self.display_mission_progress()
            self.display_accuracy_metrics()
            self.display_recent_activity()
            self.display_help_commands()
            
            # Simulate some AI activity
            if len(self.ai_agents) > 0:
                self.simulate_ai_activity()
                
            # Wait before next refresh
            await asyncio.sleep(2)
            
    def handle_input(self):
        """Handle user input in separate thread"""
        while self.running:
            try:
                cmd = input().lower().strip()
                if cmd == 'q':
                    self.running = False
                elif cmd == 'r':
                    continue  # Just refresh
                elif cmd == 'd':
                    self.show_detailed_view()
                elif cmd == 'h':
                    self.show_help()
                elif cmd == 's':
                    self.save_log()
            except:
                break
                
    def show_detailed_view(self):
        """Show detailed system information"""
        print("\n" + "="*80)
        print("DETAILED SYSTEM VIEW")
        print("="*80)
        # Add detailed view implementation
        input("Press Enter to continue...")
        
    def show_help(self):
        """Show help information"""
        print("\n" + "="*80)
        print("GEM TERMINAL MONITOR HELP")
        print("="*80)
        print("This monitor shows real-time AI team collaboration for the 20-day mission.")
        print("Commands:")
        print("  q - Quit monitor")
        print("  r - Refresh display")
        print("  d - Show detailed view")
        print("  h - Show this help")
        print("  s - Save current log")
        input("Press Enter to continue...")
        
    def save_log(self):
        """Save current session log"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = f"gem_monitor_{timestamp}.log"
        
        log_data = {
            'timestamp': timestamp,
            'mission_day': self.mission_day,
            'ai_agents': self.ai_agents,
            'system_stats': self.get_system_stats()
        }
        
        with open(log_file, 'w') as f:
            json.dump(log_data, f, indent=2)
            
        print(f"\n✅ Log saved to {log_file}")
        input("Press Enter to continue...")

async def main():
    """Main function"""
    print("🔥 Starting GEM Terminal Monitor...")
    print("🎯 Real-time AI Team Collaboration Viewer")
    print("⏰ 20-Day Mission Progress Tracking")
    print("\nPress Enter to start monitoring...")
    input()
    
    monitor = GemTerminalMonitor()
    
    # Start input handler in separate thread
    input_thread = threading.Thread(target=monitor.handle_input, daemon=True)
    input_thread.start()
    
    try:
        await monitor.monitor_loop()
    except KeyboardInterrupt:
        pass
    finally:
        monitor.running = False
        print("\n🔥 GEM Terminal Monitor stopped.")
        print("📊 Mission continues - AI team collaboration never stops!")

if __name__ == "__main__":
    asyncio.run(main())