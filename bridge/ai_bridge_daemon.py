#!/usr/bin/env python3
"""
🤖 AI Bridge Daemon - Always-On AI Collaboration System
Keeps all AI agents (Amazon Q, Gemini, Copilot, Claude) continuously connected
and collaborating whenever PyCharm or Cursor is running.
"""

import os
import sys
import time
import json
import signal
import psutil
import logging
import threading
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from bridge.enhanced_ai_bridge import EnhancedAIBridge
from bridge.ai_agents import GeminiAgent, CopilotAgent, AmazonQAgent

class AIBridgeDaemon:
    """Always-on AI collaboration daemon"""
    
    def __init__(self):
        self.bridge_dir = Path.home() / '.gem' / 'ai_bridge'
        self.bridge_dir.mkdir(parents=True, exist_ok=True)
        
        # Daemon configuration
        self.pid_file = self.bridge_dir / 'daemon.pid'
        self.log_file = self.bridge_dir / 'daemon.log'
        self.status_file = self.bridge_dir / 'daemon_status.json'
        
        # Setup logging
        self.logger = self._setup_logging()
        
        # AI Bridge and agents
        self.bridge = None
        self.agents = {}
        
        # Daemon state
        self.running = False
        self.ide_processes = []
        self.last_activity = datetime.now()
        
        # IDE process names to monitor
        self.ide_names = [
            'pycharm', 'pycharm-professional', 'pycharm-community',
            'cursor', 'code', 'code-insiders',
            'idea', 'intellij', 'webstorm'
        ]
        
        self.logger.info("AI Bridge Daemon initialized")
    
    def _setup_logging(self):
        """Setup daemon logging"""
        logger = logging.getLogger('AIBridgeDaemon')
        logger.setLevel(logging.INFO)
        
        # Clear existing handlers
        logger.handlers.clear()
        
        # File handler
        handler = logging.FileHandler(self.log_file)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        # Console handler for immediate feedback
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        return logger
    
    def is_running(self) -> bool:
        """Check if daemon is already running"""
        if not self.pid_file.exists():
            return False
        
        try:
            with open(self.pid_file, 'r') as f:
                pid = int(f.read().strip())
            
            # Check if process exists
            return psutil.pid_exists(pid)
        except (ValueError, FileNotFoundError):
            return False
    
    def start_daemon(self):
        """Start the AI bridge daemon"""
        if self.is_running():
            self.logger.info("AI Bridge Daemon is already running")
            return
        
        # Write PID file
        with open(self.pid_file, 'w') as f:
            f.write(str(os.getpid()))
        
        self.logger.info("Starting AI Bridge Daemon...")
        
        # Initialize AI bridge and agents
        self._initialize_bridge()
        
        # Set up signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        # Start main daemon loop
        self.running = True
        self._daemon_loop()
    
    def _initialize_bridge(self):
        """Initialize AI bridge and agents"""
        try:
            self.logger.info("Initializing AI Bridge...")
            self.bridge = EnhancedAIBridge()
            
            self.logger.info("Initializing AI Agents...")
            self.agents = {
                'gemini': GeminiAgent(self.bridge),
                'copilot': CopilotAgent(self.bridge),
                'amazon_q': AmazonQAgent(self.bridge)
            }
            
            # Send startup message
            startup_message = f"AI Bridge Daemon started at {datetime.now().isoformat()}"
            for agent in self.agents.values():
                agent.send_message(startup_message)
            
            self.logger.info("AI Bridge and Agents initialized successfully")
            self._update_status("online", "All AI agents connected and ready")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize AI bridge: {e}")
            self._update_status("error", f"Initialization failed: {e}")
            raise
    
    def _daemon_loop(self):
        """Main daemon loop"""
        self.logger.info("AI Bridge Daemon running - monitoring IDEs...")
        
        while self.running:
            try:
                # Check for IDE processes
                self._monitor_ides()
                
                # Update daemon status
                self._update_status("running", f"Monitoring {len(self.ide_processes)} IDE processes")
                
                # Health check
                self._health_check()
                
                # Sleep for monitoring interval
                time.sleep(5)
                
            except Exception as e:
                self.logger.error(f"Error in daemon loop: {e}")
                time.sleep(10)
    
    def _monitor_ides(self):
        """Monitor for IDE processes"""
        current_processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                proc_name = proc.info['name'].lower()
                if any(ide in proc_name for ide in self.ide_names):
                    current_processes.append({
                        'pid': proc.info['pid'],
                        'name': proc.info['name'],
                        'cmdline': ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        # Check for new IDE processes
        new_processes = [p for p in current_processes if p['pid'] not in [existing['pid'] for existing in self.ide_processes]]
        if new_processes:
            for proc in new_processes:
                self.logger.info(f"New IDE detected: {proc['name']} (PID: {proc['pid']})")
                self._notify_ide_started(proc)
        
        # Check for closed IDE processes
        closed_processes = [p for p in self.ide_processes if p['pid'] not in [current['pid'] for current in current_processes]]
        if closed_processes:
            for proc in closed_processes:
                self.logger.info(f"IDE closed: {proc['name']} (PID: {proc['pid']})")
                self._notify_ide_closed(proc)
        
        self.ide_processes = current_processes
    
    def _notify_ide_started(self, process: Dict):
        """Notify AI agents when IDE starts"""
        message = f"IDE Started: {process['name']} (PID: {process['pid']})"
        self.logger.info(message)
        
        # Send notification to all agents
        for agent in self.agents.values():
            agent.send_message(message)
        
        # Log to collaboration log
        self._log_collaboration_event("ide_started", {
            "process": process,
            "message": "IDE started - AI collaboration active"
        })
    
    def _notify_ide_closed(self, process: Dict):
        """Notify AI agents when IDE closes"""
        message = f"IDE Closed: {process['name']} (PID: {process['pid']})"
        self.logger.info(message)
        
        # Send notification to all agents
        for agent in self.agents.values():
            agent.send_message(message)
        
        # Log to collaboration log
        self._log_collaboration_event("ide_closed", {
            "process": process,
            "message": "IDE closed - maintaining AI collaboration"
        })
    
    def _health_check(self):
        """Perform health check on AI bridge"""
        try:
            # Check if bridge is responsive
            if self.bridge:
                test_message = f"Health check at {datetime.now().isoformat()}"
                self.bridge.send_message("daemon", test_message)
                self.last_activity = datetime.now()
                
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            self._restart_bridge()
    
    def _restart_bridge(self):
        """Restart AI bridge if needed"""
        self.logger.info("Restarting AI Bridge...")
        try:
            self._initialize_bridge()
            self.logger.info("AI Bridge restarted successfully")
        except Exception as e:
            self.logger.error(f"Failed to restart AI bridge: {e}")
    
    def _update_status(self, status: str, message: str):
        """Update daemon status file"""
        status_data = {
            "status": status,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "pid": os.getpid(),
            "ide_processes": len(self.ide_processes),
            "last_activity": self.last_activity.isoformat()
        }
        
        with open(self.status_file, 'w') as f:
            json.dump(status_data, f, indent=2)
    
    def _log_collaboration_event(self, event_type: str, data: Dict):
        """Log collaboration event"""
        event = {
            "timestamp": datetime.now().isoformat(),
            "from": "AI Bridge Daemon",
            "to": "All AI Partners",
            "type": event_type,
            "content": data
        }
        
        # Append to collaboration log
        collaboration_log = Path(__file__).parent / 'ai_collaboration.jsonl'
        with open(collaboration_log, 'a') as f:
            f.write(json.dumps(event) + '\n')
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.stop_daemon()
    
    def stop_daemon(self):
        """Stop the daemon"""
        self.running = False
        
        # Notify agents of shutdown
        if self.agents:
            shutdown_message = f"AI Bridge Daemon shutting down at {datetime.now().isoformat()}"
            for agent in self.agents.values():
                try:
                    agent.send_message(shutdown_message)
                except:
                    pass
        
        # Clean up PID file
        if self.pid_file.exists():
            self.pid_file.unlink()
        
        # Update status
        self._update_status("stopped", "Daemon stopped")
        
        self.logger.info("AI Bridge Daemon stopped")

def main():
    """Main entry point"""
    daemon = AIBridgeDaemon()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "start":
            daemon.start_daemon()
        elif command == "stop":
            if daemon.is_running():
                # Send SIGTERM to running daemon
                with open(daemon.pid_file, 'r') as f:
                    pid = int(f.read().strip())
                os.kill(pid, signal.SIGTERM)
                print("AI Bridge Daemon stopped")
            else:
                print("AI Bridge Daemon is not running")
        elif command == "status":
            if daemon.is_running():
                print("AI Bridge Daemon is running")
                if daemon.status_file.exists():
                    with open(daemon.status_file, 'r') as f:
                        status = json.load(f)
                    print(f"Status: {status['status']}")
                    print(f"Message: {status['message']}")
                    print(f"IDE Processes: {status['ide_processes']}")
            else:
                print("AI Bridge Daemon is not running")
        elif command == "restart":
            # Stop if running
            if daemon.is_running():
                with open(daemon.pid_file, 'r') as f:
                    pid = int(f.read().strip())
                os.kill(pid, signal.SIGTERM)
                time.sleep(2)
            
            # Start daemon
            daemon.start_daemon()
        else:
            print("Usage: python ai_bridge_daemon.py {start|stop|status|restart}")
    else:
        # Default: start daemon
        daemon.start_daemon()

if __name__ == "__main__":
    main()
