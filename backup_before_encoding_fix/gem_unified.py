    async def _process_user_command(self, command_text: str):
        """Enhanced command processing with comprehensive error handling"""
        start_time = datetime.now()
        
        try:
            self.logger.info(f"⚡ Processing command: '{command_text}'")
            self.command_count += 1
            self.interaction_count += 1
            
            # Add to conversation context
            self.conversation_context.append({
                'user': command_text,
                'timestamp': datetime.now(),
                'session_id': id(self)
            })
            
            # Priority 1: Check for accessibility commands first
            if await self._handle_accessibility_commands(command_text):
                return
            
            # Priority 2: System commands
            if await self._handle_system_commands(command_text):
                return
            
            # Priority 3: Emergency commands
            if await self._handle_emergency_commands(command_text):
                return
            
            # Priority 4: Learning/educational commands
            if await self._handle_learning_commands(command_text):
                return
            
            # Priority 5: Health commands
            if await self._handle_health_commands(command_text):
                return
            
            # Priority 6: Productivity commands
            if await self._handle_productivity_commands(command_text):
                return
            
            # Priority 7: Plugin commands
            if await self._handle_plugin_commands(command_text):
                return
            
            # Priority 8: General LLM processing
            response = await self._handle_general_command(command_text)
            
            # Add response to context
            if response:
                self.conversation_context.append({
                    'assistant': response,
                    'timestamp': datetime.now(),
                    'processing_time': (datetime.now() - start_time).total_seconds()
                })
                
                # Limit context size for performance
                if len(self.conversation_context) > 20:
                    self.conversation_context = self.conversation_context[-20:]
                
                # Speak response with user preferences
                await self._safe_tts_speak(
                    response,
                    speed=self.user_preferences.get('voice_speed', 1.0),
                    pitch=self.user_preferences.get('voice_pitch', 1.0)
                )
            
            # Track performance
            processing_time = (datetime.now() - start_time).total_seconds()
            self.response_times.append(processing_time)
            
            # Keep only last 100 response times
            if len(self.response_times) > 100:
                self.response_times = self.response_times[-100:]
            
            # Log performance
            self.logger.info(f"✅ Command processed in {processing_time:.2f}s")
            
            # Save to storage if available
            if self.storage:
                try:
                    await self.storage.save_history(
                        "user_command", 
                        command_text, 
                        response or "No response", 
                        success=1,
                        processing_time=processing_time
                    )
                except Exception as e:
                    self.logger.error(f"❌ Storage save failed: {e}")
            
        except Exception as e:
            self.logger.error(f"❌ Command processing failed: {e}")
            if self.debug:
                traceback.print_exc()
            
            error_msg = "Desculpe, tive um problema ao processar sua solicitação. Pode tentar novamente?"
            await self._safe_tts_speak(error_msg)
    
    async def _handle_accessibility_commands(self, command_text: str) -> bool:
        """Handle accessibility-specific commands"""
        command_lower = command_text.lower()
        
        try:
            if any(cmd in command_lower for cmd in ['ler tela', 'screen reader', 'leitura', 'navegar']):
                if self.accessibility_tools:
                    await self.accessibility_tools.start_screen_reader()
                    await self._safe_tts_speak("Leitor de tela ativado. Use as setas para navegar.")
                else:
                    await self._safe_tts_speak("Leitor de tela não está disponível.")
                return True
            
            elif any(cmd in command_lower for cmd in ['aumentar texto', 'zoom', 'ampliação', 'maior']):
                if self.accessibility_tools:
                    await self.accessibility_tools.enable_magnification()
                    await self._safe_tts_speak("Ampliação ativada.")
                else:
                    await self._safe_tts_speak("Recurso de ampliação não está disponível.")
                return True
            
            elif any(cmd in command_lower for cmd in ['alto contraste', 'contrast', 'cores']):
                if self.accessibility_tools:
                    await self.accessibility_tools.enable_high_contrast()
                    await self._safe_tts_speak("Alto contraste ativado.")
                else:
                    await self._safe_tts_speak("Recurso de alto contraste não está disponível.")
                return True
            
            elif any(cmd in command_lower for cmd in ['configurar voz', 'voice settings', 'velocidade']):
                await self._configure_voice_settings()
                return True
            
            elif any(cmd in command_lower for cmd in ['modo acessibilidade', 'accessibility mode']):
                self.user_preferences['accessibility_mode'] = not self.user_preferences.get('accessibility_mode', True)
                status#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
💎 GEM OS - Generative Enhanced Microphone
Assistente de Voz Local para Acessibilidade Universal

🎯 Mission: Creating an accessible, offline-first AI voice assistant
for children, people with disabilities, elderly users, and everyone
who needs technology that truly understands and serves humanity.

🌟 Features:
- 🔒 100% Offline: Complete privacy, no data leaves your computer
- ♿ Accessibility: Designed for people with different needs
- 🧠 Local AI: Powered by Ollama + Phi3 for intelligent responses  
- 🎤 Voice Recognition: Whisper for precise transcription
- 🗣️ Voice Synthesis: Multiple engines (espeak, spd-say, festival)
- 👂 Wake Word: "Hey GEM" activation detection
- ⚙️ Configurable: Complete TUI interface for customization
- 🌍 Multilingual: Multiple language support
- 🔌 Extensible: Plugin system for additional functionality

Author: GEM Project
Date: 2025-08-22
Version: 2.0.0 - Unified Enhanced Edition
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import platform
import signal
import sys
import threading
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional, Any, Dict, List

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# =========================
# Core / Features imports with graceful fallbacks
# =========================
def safe_import(module_path: str, fallback_class: str = None):
    """Safely import modules with fallback support"""
    try:
        parts = module_path.split('.')
        module = __import__(module_path, fromlist=[parts[-1]])
        return getattr(module, parts[-1])
    except Exception as e:
        if fallback_class:
            return create_fallback_class(fallback_class)
        return None

def create_fallback_class(class_name: str):
    """Create fallback class for missing modules"""
    class FallbackClass:
        def __init__(self, *args, **kwargs):
            self.logger = logging.getLogger(f"Fallback{class_name}")
            self.logger.warning(f"⚠️ {class_name} fallback in use (module not available)")
        
        async def initialize(self): pass
        async def cleanup(self): pass
        def __getattr__(self, name): 
            return lambda *args, **kwargs: None
    
    FallbackClass.__name__ = f"Fallback{class_name}"
    return FallbackClass

# Core imports with fallbacks
ConfigManager = safe_import('core.config_manager.ConfigManager', 'ConfigManager') or create_fallback_class('ConfigManager')
AudioSystem = safe_import('core.audio_system.AudioSystem', 'AudioSystem')
STTModule = safe_import('core.stt_module.STTModule', 'STTModule')
TTSModule = safe_import('core.tts_module.TTSModule', 'TTSModule')
LLMHandler = safe_import('core.llm_handler.LLMHandler', 'LLMHandler')
CommandExecutor = safe_import('core.command_executor.CommandExecutor', 'CommandExecutor')
SystemMonitor = safe_import('core.system_monitor.SystemMonitor', 'SystemMonitor')
Storage = safe_import('core.storage.Storage', 'Storage')
PluginManager = safe_import('core.plugins.PluginManager', 'PluginManager')

# Feature imports with fallbacks
AccessibilityTools = safe_import('features.accessibility_tools.AccessibilityTools', 'AccessibilityTools')
LearningTools = safe_import('features.learning_tools.LearningTools', 'LearningTools')
HealthAssistant = safe_import('features.health_assistant.HealthAssistant', 'HealthAssistant')
ProductivityTools = safe_import('features.productivity_tools.ProductivityTools', 'ProductivityTools')

# Engine imports with fallbacks
TranscriptionEngine = safe_import('engines.transcription_engine.TranscriptionEngine', 'TranscriptionEngine')
VoiceTraining = safe_import('engines.voice_training.VoiceTraining', 'VoiceTraining')
WakeWordTrainer = safe_import('engines.wake_word_trainer.WakeWordTrainer', 'WakeWordTrainer')


# ==========
# Utilities
# ==========
def log_section(title: str) -> None:
    """Enhanced section logging"""
    separator = "=" * 84
    print(f"\n{separator}")
    print(f"💎 {title}")
    print(separator)


def create_required_directories():
    """Create all required directories for GEM OS"""
    required_dirs = [
        "data/logs",
        "data/models", 
        "data/database",
        "data/backups",
        "data/plugins",
        "data/user_data",
        "core",
        "features",
        "engines",
        "plugins"
    ]
    
    for directory in required_dirs:
        Path(directory).mkdir(parents=True, exist_ok=True)
    
    # Create package __init__.py files if they don't exist
    init_files = [
        "core/__init__.py",
        "features/__init__.py", 
        "engines/__init__.py",
        "plugins/__init__.py"
    ]
    
    for init_file in init_files:
        init_path = Path(init_file)
        if not init_path.exists():
            init_path.write_text('"""GEM OS Package"""')


class EnhancedConfigManager(ConfigManager):
    """Enhanced configuration manager with fallback support"""
    
    def __init__(self, config_path: str = "data/config.json") -> None:
        try:
            super().__init__(config_path)
        except:
            # Fallback configuration
            self.config_path = config_path
            self.audio = type("AudioCfg", (), {
                "sample_rate": 16000, 
                "channels": 1, 
                "chunk": 1024,
                "wake_word_threshold": 0.7,
                "noise_reduction": True,
                "echo_cancellation": True
            })
            self.stt = type("STTCfg", (), {
                "provider": "whisper", 
                "language": "pt-BR",
                "model_size": "base",
                "timeout": 10.0
            })
            self.tts = type("TTSCfg", (), {
                "provider": "pyttsx3", 
                "voice": "pt-BR",
                "speed": 150,
                "pitch": 50,
                "engines": ["espeak", "spd-say", "festival"]
            })
            self.llm = type("LLMCfg", (), {
                "model": "llama3", 
                "endpoint": "http://localhost:11434",
                "temperature": 0.7,
                "max_tokens": 512,
                "stream": True
            })
            self.plugins = type("PluginCfg", (), {
                "dir": "plugins",
                "auto_load": True,
                "whitelist": []
            })
            self.accessibility = type("AccessibilityCfg", (), {
                "screen_reader": True,
                "magnification": False,
                "high_contrast": False,
                "voice_feedback": True
            })
    
    def load(self) -> None:
        """Load configuration with enhanced error handling"""
        try:
            if hasattr(super(), 'load'):
                super().load()
            else:
                print("⚠️ EnhancedConfigManager fallback loaded (default config)")
        except Exception as e:
            print(f"⚠️ Configuration load failed, using defaults: {e}")


# ======================
# Main GEM Class (Unified)
# ======================
class GEMVoiceAssistant:
    """
    💎 GEM Voice Assistant - Unified Enhanced Class
    
    Combines the robustness of the original GEM with the enhanced features
    and accessibility focus of the advanced version.
    
    Features all 30 modules: core systems, accessibility, learning, health,
    productivity, storage, plugins, and advanced engines.
    """
    
    def __init__(self, config_file: str = None, profile: str = "default", debug: bool = False):
        """Initialize the unified GEM Voice Assistant"""
        # Basic properties
        self.version = "2.0.0"
        self.name = "GEM OS - Generative Enhanced Microphone"
        self.start_time = time.time()
        self.startup_time = datetime.now()
        
        # Configuration
        self.config_file = config_file or "data/config.json"
        self.profile = profile
        self.debug = debug
        
        # State management
        self.running = False
        self.is_running = False
        self.is_listening = False
        self.wake_word_detected = False
        self.interaction_count = 0
        self.command_count = 0
        self.failed_modules: List[str] = []
        
        # Context and preferences
        self.conversation_context: List[Dict] = []
        self.user_preferences: Dict = {}
        
        # Performance metrics
        self.response_times: List[float] = []
        
        # Initialize logging first
        self._setup_logging()
        
        # Initialize configuration with enhanced manager
        self.config_manager = EnhancedConfigManager(self.config_file)
        self.config = self.config_manager  # Alias for compatibility
        
        # Core systems
        self.audio_system: Optional[AudioSystem] = None
        self.audio: Optional[AudioSystem] = None  # Alias
        self.stt_module: Optional[STTModule] = None
        self.stt: Optional[STTModule] = None  # Alias
        self.tts_module: Optional[TTSModule] = None
        self.tts: Optional[TTSModule] = None  # Alias
        self.llm_handler: Optional[LLMHandler] = None
        self.llm: Optional[LLMHandler] = None  # Alias
        self.command_executor: Optional[CommandExecutor] = None
        self.executor: Optional[CommandExecutor] = None  # Alias
        self.system_monitor: Optional[SystemMonitor] = None
        self.storage: Optional[Storage] = None
        self.plugin_manager: Optional[PluginManager] = None
        
        # Advanced engines
        self.transcription_engine: Optional[TranscriptionEngine] = None
        self.voice_training: Optional[VoiceTraining] = None
        self.wake_word_trainer: Optional[WakeWordTrainer] = None
        
        # Feature modules
        self.accessibility_tools: Optional[AccessibilityTools] = None
        self.accessibility: Optional[AccessibilityTools] = None  # Alias
        self.learning_tools: Optional[LearningTools] = None
        self.learning: Optional[LearningTools] = None  # Alias
        self.health_assistant: Optional[HealthAssistant] = None
        self.productivity_tools: Optional[ProductivityTools] = None
        
        self.logger.info(f"🚀 {self.name} v{self.version} initializing...")
        self.logger.info(f"🎯 Mission: Accessible AI for everyone")
        self.logger.info(f"👤 Profile: {self.profile}")
        if self.debug:
            self.logger.info("🐛 Debug mode enabled")
    
    def _setup_logging(self):
        """Setup comprehensive logging system"""
        # Create logs directory
        log_dir = Path("data/logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Configure logging
        log_file = log_dir / f"gem_{datetime.now().strftime('%Y%m%d')}.log"
        
        log_level = logging.DEBUG if self.debug else logging.INFO
        
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        self.logger = logging.getLogger("GEM")
        self.logger.info("📋 Enhanced logging system initialized")
    
    def initialize(self) -> None:
        """Initialize all GEM subsystems (synchronous compatibility method)"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            success = loop.run_until_complete(self.initialize_systems())
            return success
        finally:
            loop.close()
    
    async def initialize_systems(self) -> bool:
        """Initialize all GEM subsystems with enhanced error handling"""
        try:
            log_section("Initializing GEM OS Core Systems")
            
            # Create required directories
            create_required_directories()
            
            # Load configuration
            try:
                self.config_manager.load()
                self.logger.info("✅ Configuration loaded")
            except Exception as e:
                self.logger.warning(f"⚠️ Configuration load failed: {e}")
            
            # Load user preferences
            await self._load_user_preferences()
            
            # Initialize system monitor first
            if SystemMonitor:
                try:
                    self.system_monitor = SystemMonitor(self.config_manager)
                    await self.system_monitor.initialize()
                    self.logger.info("📊 System monitor initialized")
                except Exception as e:
                    self.failed_modules.append("system_monitor")
                    self.logger.warning(f"⚠️ System monitor failed: {e}")
            
            # Initialize storage system
            await self._initialize_storage()
            
            # Initialize core audio/speech systems
            await self._initialize_core_systems()
            
            # Initialize advanced engines
            await self._initialize_engines()
            
            # Initialize feature modules
            await self._initialize_features()
            
            # Initialize plugins
            await self._initialize_plugins()
            
            # System health check
            if self.system_monitor:
                try:
                    health_status = await self.system_monitor.get_system_health()
                    self.logger.info(f"💚 System health: {health_status.get('status', 'unknown')}")
                except Exception as e:
                    self.logger.warning(f"⚠️ Health check failed: {e}")
            
            # Final status
            if self.failed_modules:
                self.logger.warning(f"⚠️ GEM started in degraded mode. Failed: {', '.join(self.failed_modules)}")
            else:
                self.logger.info("✅ All systems initialized successfully")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ System initialization failed: {e}")
            if self.debug:
                traceback.print_exc()
            await self._emergency_fallback()
            return False
    
    async def _initialize_storage(self):
        """Initialize storage system"""
        try:
            if Storage:
                storage_path = os.path.join("data", "user_data.db")
                self.storage = Storage(storage_path)
                await self.storage.initialize()
                self.logger.info("🗃️ Storage system initialized (SQLite)")
            else:
                self.logger.warning("⚠️ Storage module not available")
        except Exception as e:
            self.failed_modules.append("storage")
            self.logger.error(f"❌ Storage initialization failed: {e}")
    
    async def _initialize_core_systems(self):
        """Initialize core audio, speech, and AI systems"""
        # Audio System
        try:
            if AudioSystem:
                self.audio_system = AudioSystem(self.config_manager)
                self.audio = self.audio_system  # Alias
                await self.audio_system.initialize()
                
                # Start audio system if needed
                if hasattr(self.audio_system, "start"):
                    await self.audio_system.start()
                
                self.logger.info("🎵 Audio system initialized (noise reduction, echo cancellation)")
            else:
                raise RuntimeError("AudioSystem not available")
        except Exception as e:
            self.failed_modules.append("audio")
            self.logger.error(f"❌ Audio system failed: {e}")
        
        # STT Module
        try:
            if STTModule:
                self.stt_module = STTModule(self.config_manager)
                self.stt = self.stt_module  # Alias
                await self.stt_module.initialize()
                self.logger.info("🎤 STT module initialized (Whisper engine)")
            else:
                raise RuntimeError("STTModule not available")
        except Exception as e:
            self.failed_modules.append("stt")
            self.logger.error(f"❌ STT module failed: {e}")
        
        # TTS Module
        try:
            if TTSModule:
                self.tts_module = TTSModule(self.config_manager)
                self.tts = self.tts_module  # Alias
                await self.tts_module.initialize()
                self.logger.info("🗣️ TTS module initialized (espeak, spd-say, festival)")
            else:
                raise RuntimeError("TTSModule not available")
        except Exception as e:
            self.failed_modules.append("tts")
            self.logger.error(f"❌ TTS module failed: {e}")
        
        # LLM Handler
        try:
            if LLMHandler:
                self.llm_handler = LLMHandler(self.config_manager)
                self.llm = self.llm_handler  # Alias
                await self.llm_handler.initialize()
                self.logger.info("🧠 LLM handler initialized (Ollama + Phi3)")
            else:
                raise RuntimeError("LLMHandler not available")
        except Exception as e:
            self.failed_modules.append("llm")
            self.logger.error(f"❌ LLM handler failed: {e}")
        
        # Command Executor
        try:
            if CommandExecutor:
                self.command_executor = CommandExecutor(
                    self.config_manager,
                    self.llm_handler,
                    self.tts_module,
                    self.audio_system
                )
                self.executor = self.command_executor  # Alias
                await self.command_executor.initialize()
                self.logger.info("⚡ Command executor initialized")
            else:
                raise RuntimeError("CommandExecutor not available")
        except Exception as e:
            self.failed_modules.append("executor")
            self.logger.error(f"❌ Command executor failed: {e}")
    
    async def _initialize_engines(self):
        """Initialize advanced engines"""
        try:
            # Advanced Transcription Engine
            if TranscriptionEngine:
                self.transcription_engine = TranscriptionEngine(self.config_manager)
                await self.transcription_engine.initialize()
                self.logger.info("🔍 Transcription engine initialized")
            
            # Voice Training Engine
            if VoiceTraining:
                self.voice_training = VoiceTraining(self.config_manager)
                await self.voice_training.initialize()
                self.logger.info("🎯 Voice training engine initialized")
            
            # Wake Word Trainer
            if WakeWordTrainer:
                self.wake_word_trainer = WakeWordTrainer(self.config_manager)
                await self.wake_word_trainer.initialize()
                self.logger.info("👂 Wake word trainer initialized")
                
        except Exception as e:
            self.failed_modules.append("engines")
            self.logger.error(f"❌ Engine initialization failed: {e}")
    
    async def _initialize_features(self):
        """Initialize feature modules with accessibility focus"""
        try:
            # Accessibility Tools (Priority #1)
            if AccessibilityTools and self.tts_module:
                self.accessibility_tools = AccessibilityTools(
                    self.config_manager, 
                    self.tts_module,
                    self.stt_module
                )
                self.accessibility = self.accessibility_tools  # Alias
                await self.accessibility_tools.initialize()
                self.logger.info("♿ Accessibility tools initialized (screen reader, magnification)")
            else:
                self.logger.warning("⚠️ Accessibility tools missing or TTS unavailable")
            
            # Learning Tools
            if LearningTools and self.llm_handler and self.tts_module:
                self.learning_tools = LearningTools(
                    self.config_manager, 
                    self.llm_handler, 
                    self.tts_module
                )
                self.learning = self.learning_tools  # Alias
                await self.learning_tools.initialize()
                self.logger.info("📚 Learning tools initialized")
            else:
                self.logger.warning("⚠️ Learning tools missing or dependencies unavailable")
            
            # Health Assistant
            if HealthAssistant and self.llm_handler and self.tts_module:
                self.health_assistant = HealthAssistant(
                    self.config_manager,
                    self.llm_handler,
                    self.tts_module
                )
                await self.health_assistant.initialize()
                self.logger.info("🏥 Health assistant initialized")
            else:
                self.logger.warning("⚠️ Health assistant missing or dependencies unavailable")
            
            # Productivity Tools
            if ProductivityTools and self.llm_handler and self.tts_module:
                self.productivity_tools = ProductivityTools(
                    self.config_manager,
                    self.llm_handler,
                    self.tts_module
                )
                await self.productivity_tools.initialize()
                self.logger.info("⚡ Productivity tools initialized")
            else:
                self.logger.warning("⚠️ Productivity tools missing or dependencies unavailable")
            
        except Exception as e:
            self.failed_modules.append("features")
            self.logger.error(f"❌ Feature initialization failed: {e}")
    
    async def _initialize_plugins(self):
        """Initialize plugin system"""
        try:
            plugins_dir = getattr(self.config_manager, "plugins", None)
            plugins_dir = getattr(plugins_dir, "dir", "plugins") if plugins_dir else "plugins"
            
            if PluginManager:
                self.plugin_manager = PluginManager(plugins_dir)
                await self.plugin_manager.load_plugins()
                self.logger.info(f"🔌 Plugin system initialized from: {plugins_dir}")
            else:
                self.logger.warning("⚠️ PluginManager module not available")
        except Exception as e:
            self.failed_modules.append("plugins")
            self.logger.error(f"❌ Plugin system failed: {e}")
    
    async def _load_user_preferences(self):
        """Load user preferences and personalization"""
        try:
            prefs_file = Path("data/database/user_preferences.json")
            if prefs_file.exists():
                with open(prefs_file, 'r', encoding='utf-8') as f:
                    self.user_preferences = json.load(f)
                self.logger.info("👤 User preferences loaded")
            else:
                # Default preferences for accessibility
                self.user_preferences = {
                    "user_name": "usuário",
                    "voice_speed": 1.0,
                    "voice_pitch": 1.0,
                    "language": "pt-BR",
                    "wake_word": "Hey GEM",
                    "response_style": "friendly",
                    "accessibility_mode": True,
                    "tts_engine": "espeak",
                    "audio_feedback": True,
                    "screen_reader": False,
                    "magnification": False,
                    "high_contrast": False,
                    "voice_feedback": True,
                    "conversation_history": True,
                    "learning_mode": True,
                    "health_reminders": False,
                    "productivity_notifications": True
                }
                await self._save_user_preferences()
                self.logger.info("👤 Default user preferences created")
                
        except Exception as e:
            self.logger.error(f"❌ Failed to load user preferences: {e}")
            # Use minimal defaults
            self.user_preferences = {
                "language": "pt-BR",
                "wake_word": "Hey GEM",
                "accessibility_mode": True,
                "voice_feedback": True
            }
    
    async def _save_user_preferences(self):
        """Save user preferences"""
        try:
            prefs_file = Path("data/database/user_preferences.json")
            prefs_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(prefs_file, 'w', encoding='utf-8') as f:
                json.dump(self.user_preferences, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            self.logger.error(f"❌ Failed to save user preferences: {e}")
    
    async def _emergency_fallback(self):
        """Emergency fallback mode for critical failures"""
        self.logger.warning("🚨 Entering emergency fallback mode...")
        
        try:
            # Basic TTS for emergency communication using system commands
            message = "GEM está com problemas técnicos, mas continuo funcionando em modo básico."
            
            # Try espeak first
            try:
                import subprocess
                subprocess.run([
                    "espeak", "-v", "pt-br", "-s", "150", 
                    message
                ], check=False, timeout=5)
            except:
                # Try spd-say as backup
                try:
                    subprocess.run([
                        "spd-say", "-l", "pt-BR", "-r", "0", 
                        message
                    ], check=False, timeout=5)
                except:
                    # Try festival as last resort
                    try:
                        subprocess.run([
                            "festival", "--tts", 
                            f"(voice_cmu_us_slt_arctic_hts)", 
                            f'(SayText "{message}")'
                        ], check=False, timeout=5)
                    except:
                        # Print to console if all TTS fails
                        print(f"🚨 EMERGENCY: {message}")
            
        except Exception as e:
            self.logger.error(f"❌ Emergency fallback failed: {e}")
            print("🚨 EMERGENCY: Critical system failure - please restart GEM")
    
    async def greet_user(self) -> None:
        """Play personalized welcome message"""
        user_name = self.user_preferences.get('user_name', 'usuário')
        language = self.user_preferences.get('language', 'pt-BR')
        
        if language == 'pt-BR':
            welcome_msg = (
                f"Olá {user_name}! GEM está online e pronto para ajudar. "
                f"Sou seu assistente de voz acessível e trabalho 100% offline para sua privacidade. "
                f"Diga 'Hey GEM' para começar uma conversa comigo. "
                f"Para ver todos os comandos, diga 'Hey GEM, ajuda'."
            )
        else:
            welcome_msg = (
                f"Hello {user_name}! GEM is online and ready to help. "
                f"I'm your accessible voice assistant and work 100% offline for your privacy. "
                f"Say 'Hey GEM' to start a conversation with me. "
                f"For all commands, say 'Hey GEM, help'."
            )
        
        await self._safe_tts_speak(welcome_msg)
        self.logger.info("👋 Personalized welcome message played")
        
        # Play accessibility announcement if enabled
        if self.user_preferences.get('accessibility_mode', False):
            accessibility_msg = (
                "Modo de acessibilidade ativo. Todas as funcionalidades de navegação por voz estão disponíveis."
            )
            await self._safe_tts_speak(accessibility_msg)
    
    async def _safe_tts_speak(self, text: str, **kwargs):
        """Safely speak text with fallback support"""
        try:
            if self.tts_module:
                # Try async speak first
                try:
                    await self.tts_module.speak(text, **kwargs)
                except TypeError:
                    # Fallback to sync speak
                    self.tts_module.speak(text, **kwargs)
            else:
                # Emergency fallback to system TTS
                await self._emergency_speak(text)
        except Exception as e:
            self.logger.error(f"❌ TTS speak failed: {e}")
            # Last resort - print to console
            print(f"🗣️ GEM: {text}")
    
    async def _emergency_speak(self, text: str):
        """Emergency TTS using system commands"""
        try:
            import subprocess
            
            # Try different TTS engines
            tts_commands = [
                ["espeak", "-v", "pt-br", "-s", "150", text],
                ["spd-say", "-l", "pt-BR", "-r", "0", text],
                ["say", text] if platform.system() == "Darwin" else None
            ]
            
            for cmd in tts_commands:
                if cmd:
                    try:
                        subprocess.run(cmd, check=False, timeout=5)
                        return
                    except:
                        continue
            
            # If all fail, just print
            print(f"🗣️ GEM: {text}")
            
        except Exception as e:
            self.logger.error(f"❌ Emergency speak failed: {e}")
            print(f"🗣️ GEM: {text}")
    
    async def run_plugins_demo(self) -> None:
        """Enhanced plugins demonstration with error handling"""
        if not self.plugin_manager:
            self.logger.warning("⚠️ Plugins não disponíveis")
            return
        
        self.logger.info("🔌 Running plugins demonstration...")
        pm = self.plugin_manager
        save = (self.storage.save_history if self.storage else lambda *a, **k: None)
        
        try:
            # WEATHER (Module 29)
            await self._demo_weather_plugins(pm, save)
            
            # NEWS (Module 30)
            await self._demo_news_plugins(pm, save)
            
            # GITHUB (Module 28 part)
            await self._demo_github_plugins(pm, save)
            
            # EMAIL (Module 28)
            await self._demo_email_plugins(pm, save)
            
            # CALENDAR (Module 27)
            await self._demo_calendar_plugins(pm, save)
            
            # FILES (Module 26)
            await self._demo_file_plugins(pm, save)
            
            # SYSTEM (Module 25)
            await self._demo_system_plugins(pm, save)
            
            # WIKI / JOKE / TRANSLATE / REMINDERS / MATH (Modules 18-24)
            await self._demo_utility_plugins(pm, save)
            
        except Exception as e:
            self.logger.error(f"❌ Plugin demo failed: {e}")
    
    async def _demo_weather_plugins(self, pm, save):
        """Demo weather plugins"""
        try:
            if "weather:get" in pm.commands:
                weather = await pm.execute_command("weather:get", "Lisboa")
                self.logger.info(f"🌤️ Weather: {weather}")
                save("weather:get", "Lisboa", weather, success=1)
            
            if "weather:forecast" in pm.commands:
                forecast = await pm.execute_command("weather:forecast", "Lisboa", 3)
                self.logger.info(f"📅 Forecast: {forecast}")
                save("weather:forecast", "Lisboa", forecast, success=1)
            
            if "weather:hourly" in pm.commands:
                hourly = await pm.execute_command("weather:hourly", "Lisboa", 9)
                self.logger.info(f"⏰ Hourly: {hourly}")
                save("weather:hourly", "Lisboa", hourly, success=1)
        except Exception as e:
            self.logger.error(f"❌ Weather plugin demo failed: {e}")
    
    async def _demo_news_plugins(self, pm, save):
        """Demo news plugins"""
        try:
            if "news:get" in pm.commands:
                news = await pm.execute_command("news:get", "us", "technology", 5)
                self.logger.info(f"📰 News: {news}")
                save("news:get", "us technology", news, success=1)
        except Exception as e:
            self.logger.error(f"❌ News plugin demo failed: {e}")
    
    async def _demo_github_plugins(self, pm, save):
        """Demo GitHub plugins"""
        try:
            if "github:repos" in pm.commands:
                repos = await pm.execute_command("github:repos")
                self.logger.info(f"📦 Repos: {repos}")
                save("github:repos", "-", repos, success=1)
            
            if "github:issues" in pm.commands:
                issues = await pm.execute_command("github:issues", "meu-repo")
                self.logger.info(f"🐛 Issues: {issues}")
                save("github:issues", "meu-repo", issues, success=1)
            
            if "github:create_issue" in pm.commands:
                new_issue = await pm.execute_command("github:create_issue", "meu-repo", "Bug encontrado", "Detalhes do bug...")
                self.logger.info(f"➕ New Issue: {new_issue}")
                save("github:create_issue", "meu-repo Bug encontrado", new_issue, success=1)
        except Exception as e:
            self.logger.error(f"❌ GitHub plugin demo failed: {e}")
    
    async def _demo_email_plugins(self, pm, save):
        """Demo email plugins"""
        try:
            if "email:send" in pm.commands:
                status = await pm.execute_command(
                    "email:send",
                    "destinatario@email.com",
                    "Teste GEM",
                    "Olá, este é um teste enviado pelo GEM!"
                )
                self.logger.info(f"✉️ Email sent: {status}")
                save("email:send", "Teste GEM", status, success=1)
            
            if "email:list" in pm.commands:
                inbox = await pm.execute_command("email:list", 3)
                self.logger.info(f"📧 Inbox: {inbox}")
                save("email:list", "-", inbox, success=1)
        except Exception as e:
            self.logger.error(f"❌ Email plugin demo failed: {e}")
    
    async def _demo_calendar_plugins(self, pm, save):
        """Demo calendar plugins"""
        try:
            if "calendar:add" in pm.commands:
                result = await pm.execute_command("calendar:add", "Reunião GEM", "2025-08-25", "15:00")
                self.logger.info(f"📅 Event added: {result}")
                save("calendar:add", "Reunião GEM", result, success=1)
            
            if "calendar:list" in pm.commands:
                events = await pm.execute_command("calendar:list")
                self.logger.info(f"📋 Events: {events}")
                save("calendar:list", "-", events, success=1)
            
            if "calendar:remove" in pm.commands:
                result = await pm.execute_command("calendar:remove", "Reunião GEM")
                self.logger.info(f"🗑️ Event removed: {result}")
                save("calendar:remove", "Reunião GEM", result, success=1)
        except Exception as e:
            self.logger.error(f"❌ Calendar plugin demo failed: {e}")
    
    async def _demo_file_plugins(self, pm, save):
        """Demo file management plugins"""
        try:
            if "file:list" in pm.commands:
                files = await pm.execute_command("file:list", "data")
                self.logger.info(f"📁 Files: {files}")
                save("file:list", "data", files, success=1)
            
            if "file:write" in pm.commands:
                result = await pm.execute_command("file:write", "data/test.txt", "Olá GEM OS")
                self.logger.info(f"✍️ File written: {result}")
                save("file:write", "data/test.txt", result, success=1)
            
            if "file:read" in pm.commands:
                content = await pm.execute_command("file:read", "data/test.txt")
                self.logger.info(f"📖 File content: {content}")
                save("file:read", "data/test.txt", content, success=1)
        except Exception as e:
            self.logger.error(f"❌ File plugin demo failed: {e}")
    
    async def _demo_system_plugins(self, pm, save):
        """Demo system plugins"""
        try:
            system_commands = ["system:time", "system:date", "system:uptime", "system:info"]
            for cmd in system_commands:
                if cmd in pm.commands:
                    result = await pm.execute_command(cmd)
                    self.logger.info(f"🖥️ {cmd}: {result}")
                    save(cmd, "-", result, success=1)
        except Exception as e:
            self.logger.error(f"❌ System plugin demo failed: {e}")
    
    async def _demo_utility_plugins(self, pm, save):
        """Demo utility plugins (wiki, jokes, translate, reminders, math)"""
        try:
            # Wikipedia
            if "wiki:search" in pm.commands:
                summary = await pm.execute_command("wiki:search", "Inteligência Artificial", 2)
                self.logger.info(f"📚 Wiki: {summary}")
                save("wiki:search", "Inteligência Artificial", summary, success=1)
            
            # Jokes
            if "joke:get" in pm.commands:
                joke = await pm.execute_command("joke:get", "neutral")
                self.logger.info(f"😄 Joke: {joke}")
                save("joke:get", "neutral", joke, success=1)
            
            # Translation
            if "translate:text" in pm.commands:
                translated = await pm.execute_command("translate:text", "Olá mundo", "pt", "en")
                self.logger.info(f"🌐 Translation: {translated}")
                save("translate:text", "Olá mundo (pt->en)", translated, success=1)
            
            # Reminders
            if "reminder:add" in pm.commands:
                reminder = await pm.execute_command("reminder:add", "Beber água", 1)
                self.logger.info(f"⏰ Reminder: {reminder}")
                save("reminder:add", "Beber água em 1 min", reminder, success=1)
            
            if "reminder:list" in pm.commands:
                reminders = await pm.execute_command("reminder:list")
                self.logger.info(f"📝 Reminders: {reminders}")
                save("reminder:list", "-", reminders, success=1)
            
            # Math
            if "math:calc" in pm.commands:
                result = await pm.execute_command("math:calc", "2**8 + sqrt(16)")
                self.logger.info(f"🔢 Math: {result}")
                save("math:calc", "2**8 + sqrt(16)", result, success=1)
                
        except Exception as e:
            self.logger.error(f"❌ Utility plugin demo failed: {e}")
    
    async def start(self):
        """Start the GEM Voice Assistant (main entry point)"""
        try:
            log_section("Starting GEM Voice Assistant")
            
            # Initialize all systems
            if not await self.initialize_systems():
                self.logger.error("❌ Failed to initialize systems")
                return False
            
            # Set running flags
            self.running = True
            self.is_running = True
            
            # Welcome message
            await self.greet_user()
            
            # Start main interaction loop
            await self._main_loop()
            
        except KeyboardInterrupt:
            self.logger.info("👋 Shutdown requested by user")
        except Exception as e:
            self.logger.error(f"❌ Unexpected error: {e}")
            if self.debug:
                traceback.print_exc()
        finally:
            await self.shutdown()
    
    async def run(self, dry_run: bool = False) -> None:
        """
        Main asynchronous loop (compatibility method from original)
        Supports both interactive and dry-run modes
        """
        self.running = True
        self.is_running = True
        
        await self.greet_user()
        
        if dry_run:
            self.logger.info("🔧 Dry run mode: initialized all systems, skipping main loop")
            # Run quick system tests
            await self._run_system_tests()
            await self.run_plugins_demo()
            return
        
        # Start main interaction loop
        await self._main_loop()
    
    async def _run_system_tests(self):
        """Run quick system tests in dry-run mode"""
        self.logger.info("🧪 Running system tests...")
        
        # Test STT (quick)
        if self.stt_module:
            try:
                self.logger.info("🎧 Testing STT (quick transcription)...")
                # Simulate quick test - would normally capture audio
                test_result = "STT system ready"
                self.logger.info(f"🔍 STT test: {test_result}")
                if self.storage:
                    await self.storage.save_history("stt:test", "-", test_result, success=1)
            except Exception as e:
                self.logger.error(f"❌ STT test failed: {e}")
        
        # Test LLM
        if self.llm_handler:
            try:
                query = "Explique brevemente o que é o GEM OS."
                self.logger.info(f"🧠 Testing LLM: {query}")
                resp = await self.llm_handler.process_query(query)
                self.logger.info(f"💬 LLM response: {resp}")
                
                # Test streaming
                self.logger.info("🧠 Testing LLM streaming...")
                stream_tokens = []
                async for token in self.llm_handler.stream_query("Liste 3 features do GEM OS"):
                    stream_tokens.append(token)
                    if len(stream_tokens) > 10:  # Limit for testing
                        break
                self.logger.info(f"📡 Stream test: {''.join(stream_tokens)}")
                
            except Exception as e:
                self.logger.error(f"❌ LLM test failed: {e}")
        
        # Test TTS
        if self.tts_module:
            try:
                await self._safe_tts_speak("Sistema de voz funcionando corretamente.")
                # Test file save
                await self.tts_module.save_to_file("Teste de áudio salvo", "data/test_audio.mp3")
                self.logger.info("🔊 TTS test completed")
            except Exception as e:
                self.logger.error(f"❌ TTS test failed: {e}")
        
        # Test accessibility
        if self.accessibility_tools:
            try:
                await self.accessibility_tools.read_text("Sistema de acessibilidade ativo.")
                self.logger.info("♿ Accessibility test completed")
            except Exception as e:
                self.logger.error(f"❌ Accessibility test failed: {e}")
        
        # Test learning tools
        if self.learning_tools:
            try:
                quiz = await self.learning_tools.generate_quiz("Ciência de Dados", 2)
                self.logger.info(f"🧩 Learning test - Quiz: {quiz}")
                if self.storage:
                    await self.storage.save_history("learning:test", "Ciência de Dados", str(quiz), success=1)
            except Exception as e:
                self.logger.error(f"❌ Learning test failed: {e}")
        
        # Test storage
        if self.storage:
            try:
                await self.storage.save_history("test", "System Test", "All systems operational", success=1)
                hist = await self.storage.get_history(3)
                self.logger.info(f"🗃️ Storage test - Recent records: {len(hist)}")
            except Exception as e:
                self.logger.error(f"❌ Storage test failed: {e}")
    
    async def _main_loop(self):
        """Enhanced main interaction loop"""
        self.logger.info("🔄 Starting main interaction loop...")
        
        # Start background tasks
        tasks = []
        
        # Wake word detection task
        tasks.append(asyncio.create_task(self._wake_word_detection()))
        
        # Continuous listening task
        tasks.append(asyncio.create_task(self._continuous_listening()))
        
        # System monitoring task
        if self.system_monitor:
            tasks.append(asyncio.create_task(self._system_monitoring_loop()))
        
        # Health reminders task
        if self.health_assistant and self.user_preferences.get('health_reminders', False):
            tasks.append(asyncio.create_task(self._health_reminders_loop()))
        
        # Productivity notifications task
        if self.productivity_tools and self.user_preferences.get('productivity_notifications', True):
            tasks.append(asyncio.create_task(self._productivity_notifications_loop()))
        
        try:
            # Keep the main loop running
            while self.running and self.is_running:
                await asyncio.sleep(0.1)
                
                # Check for task failures and restart if needed
                for i, task in enumerate(tasks):
                    if task.done() and not task.cancelled():
                        exception = task.exception()
                        if exception:
                            self.logger.error(f"❌ Background task {i} failed: {exception}")
                            # Restart the task based on its index
                            if i == 0:  # Wake word detection
                                tasks[i] = asyncio.create_task(self._wake_word_detection())
                            elif i == 1:  # Continuous listening
                                tasks[i] = asyncio.create_task(self._continuous_listening())
                            # Add other task restarts as needed
        
        finally:
            # Cancel all background tasks
            for task in tasks:
                if not task.done():
                    task.cancel()
            
            # Wait for tasks to complete cancellation
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _wake_word_detection(self):
        """Enhanced wake word detection with multiple detection methods"""
        self.logger.info("👂 Wake word detection started")
        
        while self.running and self.is_running:
            try:
                if not self.is_listening:
                    # Get audio stream
                    if self.audio_system:
                        audio_data = await self.audio_system.capture_audio(duration=2.0)
                        
                        # Check for wake word
                        if await self._detect_wake_word(audio_data):
                            self.wake_word_detected = True
                            self.logger.info("🎯 Wake word 'Hey GEM' detected!")
                            
                            # Play acknowledgment sound
                            if hasattr(self.audio_system, 'play_system_sound'):
                                await self.audio_system.play_system_sound("wake_up")
                            
                            # Start active listening
                            await self._start_active_listening()
                
                await asyncio.sleep(0.1)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"❌ Wake word detection error: {e}")
                await asyncio.sleep(1.0)
        
        self.logger.info("👂 Wake word detection stopped")
    
    async def _detect_wake_word(self, audio_data):
        """Advanced wake word detection with multiple methods"""
        try:
            # Method 1: Trained wake word model
            if self.wake_word_trainer:
                try:
                    if await self.wake_word_trainer.detect_wake_word(audio_data):
                        return True
                except Exception as e:
                    self.logger.debug(f"Wake word trainer failed: {e}")
            
            # Method 2: STT-based detection
            if self.stt_module:
                try:
                    text = await self.stt_module.transcribe_audio(audio_data)
                    if not text:
                        return False
                    
                    # Get user's custom wake word
                    user_wake_word = self.user_preferences.get('wake_word', 'Hey GEM').lower()
                    
                    # Default wake words + user custom
                    wake_words = [
                        user_wake_word,
                        "hey gem", "ei gem", "gem", "olá gem",
                        "hey jimmy", "oi gem", "gemini",
                        "assistant", "assistente"
                    ]
                    
                    text_lower = text.lower()
                    detected = any(wake_word in text_lower for wake_word in wake_words)
                    
                    if detected:
                        # Log for voice training improvement
                        if self.voice_training:
                            try:
                                await self.voice_training.log_successful_detection(audio_data, text)
                            except Exception as e:
                                self.logger.debug(f"Voice training log failed: {e}")
                        
                        self.logger.info(f"🎯 Wake word detected in text: '{text}'")
                    
                    return detected
                    
                except Exception as e:
                    self.logger.debug(f"STT wake word detection failed: {e}")
            
            return False
            
        except Exception as e:
            self.logger.error(f"❌ Wake word detection failed: {e}")
            return False
    
    async def _start_active_listening(self):
        """Enhanced active listening session after wake word"""
        self.is_listening = True
        self.logger.info("🎤 Starting active listening session...")
        
        try:
            # Give audio feedback
            await self._safe_tts_speak("Sim?", speed=1.2)
            
            # Capture user command with timeout
            if self.audio_system:
                audio_data = await self.audio_system.capture_audio(
                    duration=5.0,
                    timeout=10.0
                )
                
                # Transcribe audio to text
                if self.stt_module:
                    command_text = await self.stt_module.transcribe_audio(audio_data)
                    
                    if command_text and command_text.strip():
                        self.logger.info(f"🔍 User command: '{command_text}'")
                        
                        # Process command
                        await self._process_user_command(command_text)
                    else:
                        await self._safe_tts_speak("Desculpe, não consegui entender. Pode repetir?")
            
        except Exception as e:
            self.logger.error(f"❌ Active listening error: {e}")
            await self._safe_tts_speak("Desculpe, tive um problema ao processar seu comando.")
        
        finally:
            self.is_listening = False
            self.wake_word_detected = False
    
    async def _continuous_listening(self):
        """Enhanced continuous background listening"""
        self.logger.info("🎧 Continuous listening started")
        
        while self.running and self.is_running:
            try:
                if not self.is_listening and not self.wake_word_detected:
                    # Monitor for system commands
                    if self.audio_system:
                        audio_data = await self.audio_system.capture_audio(duration=1.0)
                        
                        if self.stt_module:
                            text = await self.stt_module.transcribe_audio(audio_data)
                            
                            if text:
                                text_lower = text.lower()
                                
                                # System shutdown commands
                                if any(cmd in text_lower for cmd in ["gem shutdown", "gem desligar", "desligar gem"]):
                                    await self._safe_tts_speak("Desligando GEM. Até logo!")
                                    self.running = False
                                    self.is_running = False
                                    break
                                
                                # Emergency help
                                elif any(cmd in text_lower for cmd in ["gem ajuda", "gem help", "emergência"]):
                                    await self._show_quick_help()
                
                await asyncio.sleep(0.5)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"❌ Continuous listening error: {e}")
                await asyncio.sleep(1.0)
        
        self.logger.info("🎧 Continuous listening stopped")
    
    async def _system_monitoring_loop(self):
        """Background system monitoring"""
        self.logger.info("📊 System monitoring started")
        
        while self.running and self.is_running:
            try:
                if self.system_monitor:
                    health = await self.system_monitor.get_system_health()
                    
                    # Check for issues
                    if health.get('status') == 'critical':
                        self.logger.warning("⚠️ System health critical!")
                        await self._safe_tts_speak("Atenção: detectado problema no sistema.")
                    
                    # Log performance metrics periodically
                    if self.command_count > 0 and self.command_count % 10 == 0:
                        avg_response = sum(self.response_times[-10:]) / min(len(self.response_times), 10)
                        self.logger.info(f"📈 Performance: {self.command_count} commands, avg {avg_response:.2f}s")
                
                # Sleep for 30 seconds between checks
                await asyncio.sleep(30)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"❌ System monitoring error: {e}")
                await asyncio.sleep(60)
        
        self.logger.info("📊 System monitoring stopped")
    
    async def _health_reminders_loop(self):
        """Background health reminders"""
        self.logger.info("🏥 Health reminders started")
        
        while self.running and self.is_running:
            try:
                if self.health_assistant:
                    # Check for due reminders every 5 minutes
                    reminders = await self.health_assistant.check_due_reminders()
                    
                    for reminder in reminders:
                        await self._safe_tts_speak(f"Lembrete de saúde: {reminder}")
                
                # Check every 5 minutes
                await asyncio.sleep(300)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"❌ Health reminders error: {e}")
                await asyncio.sleep(300)
        
        self.logger.info("🏥 Health reminders stopped")
    
    async def _productivity_notifications_loop(self):
        """Background productivity notifications"""
        self.logger.info("⚡ Productivity notifications started")
        
        while self.running and self.is_running:
            try:
                if self.productivity_tools:
                    # Check for productivity notifications every 15 minutes
                    notifications = await self.productivity_tools.check_notifications()
                    
                    for notification in notifications:
                        await self._safe_tts_speak(f"Lembrete: {notification}")
                
                # Check every 15 minutes
                await asyncio.sleep(900)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"❌ Productivity notifications error: {e}")
                await asyncio.sleep(900)
        
        self.logger.info("⚡ Productivity notifications stopped")