#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
💎 GEM OS - System Checker
Complete system verification and status report
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple

class GEMSystemChecker:
    """Comprehensive system checker for GEM OS."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.results = {}
    
    def check_executable_status(self) -> Dict[str, bool]:
        """Check if gem_runner.sh is executable."""
        runner_path = self.project_root / "gem_runner.sh"
        
        status = {
            'exists': runner_path.exists(),
            'executable': False,
            'path': str(runner_path)
        }
        
        if status['exists']:
            status['executable'] = os.access(runner_path, os.X_OK)
        
        return status
    
    def check_core_files(self) -> Dict[str, bool]:
        """Check if all core files exist."""
        core_files = [
            'gem.py',
            'gem_runner.sh',
            'requirements.txt',
            'core/audio_system.py',
            'core/tts_module.py',
            'core/stt_module.py',
            'core/config_manager.py',
            'bridge/ai_bridge.py',
            'bridge/ai_agents.py',
            'features/accessibility_tools.py',
            'features/health_assistant.py'
        ]
        
        status = {}
        for file_path in core_files:
            full_path = self.project_root / file_path
            status[file_path] = full_path.exists()
        
        return status
    
    def check_voice_engines(self) -> Dict[str, bool]:
        """Check available TTS engines."""
        engines = {}
        
        # Check pyttsx3
        try:
            import pyttsx3
            engines['pyttsx3'] = True
        except ImportError:
            engines['pyttsx3'] = False
        
        # Check espeak
        try:
            result = subprocess.run(['espeak', '--version'], 
                                  capture_output=True, timeout=5)
            engines['espeak'] = result.returncode == 0
        except:
            engines['espeak'] = False
        
        # Check edge-tts
        try:
            import edge_tts
            engines['edge_tts'] = True
        except ImportError:
            engines['edge_tts'] = False
        
        # Check gtts
        try:
            from gtts import gTTS
            engines['gtts'] = True
        except ImportError:
            engines['gtts'] = False
        
        return engines
    
    def check_ai_bridge(self) -> Dict[str, bool]:
        """Check AI bridge system status."""
        bridge_status = {}
        
        # Check bridge files
        bridge_files = [
            'bridge/__init__.py',
            'bridge/ai_bridge.py',
            'bridge/ai_agents.py'
        ]
        
        for file_path in bridge_files:
            full_path = self.project_root / file_path
            bridge_status[f'file_{file_path}'] = full_path.exists()
        
        # Check bridge logs
        bridge_dir = Path.home() / '.gem' / 'ai_bridge'
        bridge_status['logs_directory'] = bridge_dir.exists()
        
        if bridge_dir.exists():
            bridge_status['shared_log'] = (bridge_dir / 'shared.json').exists()
            bridge_status['bridge_log'] = (bridge_dir / 'bridge.log').exists()
        
        return bridge_status
    
    def run_complete_check(self) -> Dict[str, Dict]:
        """Run complete system check."""
        print("🔍 Running GEM OS System Check...")
        
        self.results = {
            'executable': self.check_executable_status(),
            'core_files': self.check_core_files(),
            'voice_engines': self.check_voice_engines(),
            'ai_bridge': self.check_ai_bridge()
        }
        
        return self.results
    
    def print_report(self):
        """Print detailed system report."""
        print("\n" + "="*60)
        print("💎 GEM OS SYSTEM STATUS REPORT")
        print("="*60)
        
        # Executable status
        print("\n🚀 EXECUTABLE STATUS:")
        exec_status = self.results['executable']
        print(f"  gem_runner.sh exists: {'✅' if exec_status['exists'] else '❌'}")
        print(f"  gem_runner.sh executable: {'✅' if exec_status['executable'] else '❌'}")
        
        # Core files
        print("\n📁 CORE FILES:")
        core_files = self.results['core_files']
        for file_path, exists in core_files.items():
            print(f"  {file_path}: {'✅' if exists else '❌'}")
        
        # Voice engines
        print("\n🎤 VOICE ENGINES:")
        voice_engines = self.results['voice_engines']
        for engine, available in voice_engines.items():
            print(f"  {engine}: {'✅' if available else '❌'}")
        
        # AI Bridge
        print("\n🤖 AI BRIDGE SYSTEM:")
        bridge_status = self.results['ai_bridge']
        for component, status in bridge_status.items():
            print(f"  {component}: {'✅' if status else '❌'}")
        
        # Summary
        print("\n📊 SUMMARY:")
        total_checks = sum(len(section) for section in self.results.values())
        passed_checks = sum(
            sum(1 for status in section.values() if status) 
            for section in self.results.values()
        )
        
        print(f"  Total checks: {total_checks}")
        print(f"  Passed: {passed_checks}")
        print(f"  Failed: {total_checks - passed_checks}")
        print(f"  Success rate: {(passed_checks/total_checks)*100:.1f}%")
        
        if passed_checks == total_checks:
            print("\n🎉 ALL SYSTEMS OPERATIONAL!")
        else:
            print("\n⚠️  Some issues detected. Check failed items above.")

if __name__ == "__main__":
    checker = GEMSystemChecker()
    checker.run_complete_check()
    checker.print_report()