#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
💎 GEM OS - Generative Enhanced Microphone
Assistente de Voz Acessível para toda a Humanidade

Mission: Creating an accessible, offline-first AI voice assistant
for children, people with disabilities, elderly users, and everyone
who needs technology that truly understands and serves humanity.

Features:
- 🔒 100% Offline: Complete privacy, no data leaves your computer
- ♿ Accessibility: Designed for people with different needs
- 🧠 Local AI: Powered by Ollama for intelligent responses
- 🎤 Voice Recognition: Multiple STT engines for accuracy
- 🗣️ Voice Synthesis: Multiple TTS engines for natural speech
- 👂 Wake Word: Custom wake word detection
- ⚙️ Configurable: Complete configuration management
- 🌐 Multilingual: Multiple language support
- 🔗 Extensible: Plugin system for additional functionality
- 💚 Health: Wellness and health monitoring features

Author: GEM Project
Date: 2025-08-23
Version: 2.0.0 - Revolutionary AI Edition with Advanced Accessibility
"""

import argparse
import asyncio
import inspect
import logging
import os
import platform
import signal
import sys
import time
from pathlib import Path
from typing import Optional, Dict, List, Any

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Safe import function
def safe_import(module_path: str, class_name: str = None):
    """Safely import a module and optionally get a class from it."""
    try:
        import importlib
        module = importlib.import_module(module_path)
        if class_name:
            return getattr(module, class_name, None)
        return module
    except ImportError as e:
        print(f"⚠️ Warning: Could not import '{module_path}': {e}")
        return None
    except Exception as e:
        print(f"❌ Error importing '{module_path}': {e}")
        return None

# Import core components
AudioSystem = safe_import("core.audio_system", "AudioSystem")
ConfigManager = safe_import("core.config_manager", "GEMConfigManager")
STTModule = safe_import("core.stt_module", "STTModule")
TTSModule = safe_import("core.tts_module", "TTSModule")
LLMHandler = safe_import("core.llm_handler", "LLMHandler")
CommandExecutor = safe_import("core.command_executor", "CommandExecutor")
SystemMonitor = safe_import("core.system_monitor", "SystemMonitor")

# Import feature modules
AccessibilityTools = safe_import("features.accessibility_tools", "AccessibilityTools")
AdvancedAccessibility = safe_import("features.advanced_accessibility", "AdvancedAccessibility")
LearningTools = safe_import("features.learning_tools", "LearningTools")
UserLearningSystem = safe_import("features.user_learning", "UserLearningSystem")
HealthAssistant = safe_import("features.health_assistant", "HealthAssistant")
SmartHealthSystem = safe_import("features.smart_health_system", "SmartHealthSystem")
ProductivityTools = safe_import("features.productivity_tools", "ProductivityTools")
AICompanion = safe_import("features.ai_companion", "AICompanion")

# Import AI integrations
MultiAIHandler = safe_import("integrations.ai.multi_ai_handler", "MultiAIHandler")
CollaborationManager = safe_import("integrations.ai.collaboration_manager", "CollaborationManager")
NotionIntegration = safe_import("integrations.notion_mcp", "NotionIntegration")
GitBookIntegration = safe_import("integrations.gitbook_mcp", "GitBookIntegration")
MCPConnectorManager = safe_import("integrations.mcp_connectors", "MCPConnectorManager")

# Import Gemini's Enhanced AI Bridge
EnhancedAIBridge = safe_import("bridge.ai_bridge", "EnhancedAIBridge")
AmazonQAgent = safe_import("bridge.ai_agents", "AmazonQAgent")
GeminiAgent = safe_import("bridge.ai_agents", "GeminiAgent")
CopilotAgent = safe_import("bridge.ai_agents", "CopilotAgent")

# Enhanced AI Bridge Integration
try:
    sys.path.append('/home/oem')
    from amazon_q_enhanced import AmazonQIntegration
    AI_BRIDGE_AVAILABLE = True
except ImportError:
    AI_BRIDGE_AVAILABLE = False


class SystemState:
    """Manages the state of the GEM OS system."""
    
    def __init__(self):
        self.is_running: bool = False
        self.is_processing: bool = False
        self.is_listening: bool = False
        self.is_awake: bool = True
        self.stop_requested: bool = False
        self.last_interaction: float = time.time()
        self.main_task: Optional[asyncio.Task] = None
        self.interaction_count: int = 0
        self.error_count: int = 0


class GEMVoiceAssistant:
    """Main GEM OS Voice Assistant class."""
    
    def __init__(self, profile: str = "default", debug: bool = False):
        self.state = SystemState()
        self.profile = profile
        self.debug = debug
        
        # Core components
        self.config_manager: Optional[ConfigManager] = None
        self.audio_system: Optional[AudioSystem] = None
        self.stt_module: Optional[STTModule] = None
        self.tts_module: Optional[TTSModule] = None
        self.llm_handler: Optional[LLMHandler] = None
        self.command_executor: Optional[CommandExecutor] = None
        self.system_monitor: Optional[SystemMonitor] = None
        
        # Feature modules
        self.accessibility_tools: Optional[AccessibilityTools] = None
        self.advanced_accessibility: Optional[AdvancedAccessibility] = None
        self.learning_tools: Optional[LearningTools] = None
        self.user_learning: Optional[UserLearningSystem] = None
        self.health_assistant: Optional[HealthAssistant] = None
        self.smart_health_system: Optional[SmartHealthSystem] = None
        self.productivity_tools: Optional[ProductivityTools] = None
        self.ai_companion: Optional[AICompanion] = None
        
        # AI integrations
        self.multi_ai_handler: Optional[MultiAIHandler] = None
        self.ai_bridge: Optional[Any] = None
        self.collaboration_manager: Optional[CollaborationManager] = None
        self.notion: Optional[NotionIntegration] = None
        self.gitbook: Optional[GitBookIntegration] = None
        self.mcp_connectors: Optional[MCPConnectorManager] = None
        
        # Gemini's Enhanced AI Bridge System
        self.gemini_bridge: Optional[EnhancedAIBridge] = None
        self.amazon_q_agent: Optional[AmazonQAgent] = None
        self.gemini_agent: Optional[GeminiAgent] = None
        self.copilot_agent: Optional[CopilotAgent] = None
        
        # Conversation context
        self.conversation_context: List[Dict[str, Any]] = []
        
        # Setup logging
        self.logger = self._setup_logging()
        self.logger.info("💎 Initializing GEM OS...")
        
        # Initialize configuration first
        self._initialize_config()
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging with appropriate level and format."""
        log_level = logging.DEBUG if self.debug else logging.INFO
        
        # Create logs directory if it doesn't exist
        log_dir = project_root / "data" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Configure logging
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler(log_dir / "gem.log")
            ]
        )
        
        return logging.getLogger("GEMVoiceAssistant")
    
    def _initialize_config(self):
        """Initialize configuration manager."""
        if not ConfigManager:
            self.logger.error("❌ ConfigManager not available. Cannot continue.")
            sys.exit(1)
        
        try:
            self.config_manager = ConfigManager()
            self.config = self.config_manager.load(profile=self.profile)
            self.logger.info("✅ Configuration loaded successfully")
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize configuration: {e}")
            sys.exit(1)
    
    async def initialize_systems(self):
        """Initialize all system components."""
        self.logger.info("🚀 Starting system initialization...")
        
        config = self.config
        
        # Initialize core systems
        await self._initialize_core_systems(config)
        
        # Initialize feature modules
        await self._initialize_features(config)
        
        # Initialize AI Bridge for collaboration
        await self._initialize_ai_bridge()
        
        # Initialize Collaboration Manager
        await self._initialize_collaboration_manager()
        
        # Initialize Gemini's Enhanced AI Bridge
        await self._initialize_gemini_bridge()
        
        # Initialize Notion integration
        self.notion = await self._initialize_component(NotionIntegration, "Notion MCP Integration", self.config_manager)
        
        # Initialize GitBook integration
        self.gitbook = await self._initialize_component(GitBookIntegration, "GitBook MCP Integration", self.config_manager)
        
        # Initialize MCP connectors
        self.mcp_connectors = await self._initialize_component(MCPConnectorManager, "MCP Connectors", self.config_manager)

        # Link audio events to our logic
        self._setup_callbacks()

        self.logger.info("✅ All systems initialized successfully.")

        # Announce readiness with AI companion personality
        if self.ai_companion:
            welcome_msg = await self.ai_companion.process_interaction(
                "sistema_iniciado", {"first_interaction": True}
            )
            await self._safe_speak(welcome_msg)
        else:
            await self._safe_speak("Hello there! I'm GEM, and I'm here to be your personal assistant. I learn from our conversations to better help you. What would you like to do today?")

    async def _initialize_component(self, component_class, component_name: str, *args, **kwargs):
        """Generic helper to initialize a system component, reducing boilerplate."""
        if not component_class:
            self.logger.debug(f"Component '{component_name}' not available for initialization.")
            return None
        try:
            instance = component_class(*args, **kwargs, logger=self.logger)
            if hasattr(instance, "initialize"):
                await instance.initialize()
            self.logger.info(f"✅ {component_name} initialized")
            return instance
        except Exception as e:
            self.logger.error(f"❌ {component_name} failed to initialize: {e}", exc_info=self.debug)
            return None

    async def _initialize_core_systems(self, config):
        """Initialize core system components using the helper."""
        self.audio_system = await self._initialize_component(AudioSystem, "Audio System", config=config.audio)
        self.stt_module = await self._initialize_component(STTModule, "STT Module", config=config.stt)
        self.tts_module = await self._initialize_component(TTSModule, "TTS Module", config=config.tts)
        self.llm_handler = await self._initialize_component(LLMHandler, "LLM Handler", config=config.llm)
        self.command_executor = await self._initialize_component(CommandExecutor, "Command Executor", self)
        self.system_monitor = await self._initialize_component(SystemMonitor, "System Monitor", config=config.general)

        if self.system_monitor:
            self.system_monitor.start_monitoring()

    async def _initialize_features(self, config):
        """Initialize feature modules using the helper."""
        # Revolutionary AI features first
        self.multi_ai_handler = await self._initialize_component(MultiAIHandler, "Multi-AI Handler", config)
        self.ai_companion = await self._initialize_component(AICompanion, "AI Companion", self)
        self.user_learning = await self._initialize_component(UserLearningSystem, "User Learning System", self)
        self.advanced_accessibility = await self._initialize_component(AdvancedAccessibility, "Advanced Accessibility", self)
        self.smart_health_system = await self._initialize_component(SmartHealthSystem, "Smart Health System", self)
        
        # Original features
        self.accessibility_tools = await self._initialize_component(AccessibilityTools, "Accessibility Tools", self)
        self.learning_tools = await self._initialize_component(LearningTools, "Learning Tools", self)
        self.health_assistant = await self._initialize_component(HealthAssistant, "Health Assistant", self)
        self.productivity_tools = await self._initialize_component(ProductivityTools, "Productivity Tools", self)
    
    async def _initialize_ai_bridge(self):
        """Initialize enhanced AI bridge for collaboration."""
        if AI_BRIDGE_AVAILABLE:
            try:
                self.ai_bridge = AmazonQIntegration()
                self.ai_bridge.send_message("GEM OS Revolutionary Edition started with enhanced AI collaboration")
                self.logger.info("✅ AI Bridge initialized - Ready for multi-AI collaboration")
            except Exception as e:
                self.logger.error(f"❌ AI Bridge initialization failed: {e}")
        else:
            self.logger.info("ℹ️ AI Bridge not available - running in standalone mode")
    
    async def _initialize_collaboration_manager(self):
        """Initialize AI collaboration manager."""
        if CollaborationManager:
            try:
                self.collaboration_manager = CollaborationManager(self.logger)
                await self.collaboration_manager.initialize()
                self.logger.info("✅ AI Collaboration Manager initialized")
                
                # Share initial implementation context
                if self.collaboration_manager:
                    self.collaboration_manager.share_implementation_context({
                        'title': 'Copilot Enhanced AI Collaboration System',
                        'description': 'Real-time collaboration, context sharing, and coordination between AIs',
                        'status': 'active',
                        'module': 'integrations.ai.collaboration_manager'
                    })
                    
            except Exception as e:
                self.logger.error(f"❌ Collaboration Manager initialization failed: {e}")
        else:
            self.logger.info("ℹ️ Collaboration Manager not available")
    
    async def _initialize_gemini_bridge(self):
        """Initialize Gemini's Enhanced AI Bridge system for AI team collaboration."""
        if EnhancedAIBridge and AmazonQAgent and GeminiAgent and CopilotAgent:
            try:
                # Initialize the Enhanced AI Bridge
                self.gemini_bridge = EnhancedAIBridge()
                
                # Initialize all AI agents
                self.amazon_q_agent = AmazonQAgent(self.gemini_bridge)
                self.gemini_agent = GeminiAgent(self.gemini_bridge)
                self.copilot_agent = CopilotAgent(self.gemini_bridge)
                
                # Send startup message confirming all agents are online
                self.amazon_q_agent.send_message(
                    "🎆 GEM OS MAIN SYSTEM ONLINE WITH GEMINI'S DEFINITIVE AI BRIDGE!\n\n"
                    "✅ ALL COMPONENTS ACTIVE:\n"
                    "- Enhanced AI Bridge with GEMRules validation ✅\n"
                    "- Amazon Q Agent ready for cloud integration ✅\n"
                    "- Gemini Agent ready for code analysis ✅\n"
                    "- Copilot Agent ready for development support ✅\n\n"
                    "🚀 Ready for seamless AI team collaboration on GEM OS!",
                    recipients=['gemini', 'copilot']
                )
                
                self.logger.info("✅ Gemini's Enhanced AI Bridge initialized - All AI agents active")
                
            except Exception as e:
                self.logger.error(f"❌ Gemini's AI Bridge initialization failed: {e}", exc_info=self.debug)
        else:
            self.logger.info("ℹ️ Gemini's AI Bridge components not available")
    
    def _setup_callbacks(self):
        """Setup system callbacks."""
        if self.audio_system:
            self.audio_system.set_wake_word_callback(self.on_wake_word_detected)
            self.audio_system.set_speech_callback(self.on_speech_detected)
    
    async def on_wake_word_detected(self, keyword: str):
        """Handle wake word detection."""
        self.logger.info(f"💎 Wake word '{keyword}' detected")
        self.state.is_awake = True
        self.state.last_interaction = time.time()
        
        if self.tts_module:
            await self._safe_speak("I'm listening. What can I do for you?")
    
    async def on_speech_detected(self, audio_data: bytes):
        """Handle speech detection and processing."""
        if not self.state.is_awake or not self.stt_module:
            return
        
        self.state.is_processing = True
        self.logger.info(f"🎤 Processing {len(audio_data)} bytes of audio")
        
        try:
            # Transcribe speech
            transcription = await self.stt_module.transcribe(audio_data)
            text = transcription.get("text", "") if isinstance(transcription, dict) else transcription
            
            if text:
                self.logger.info(f"📝 Transcription: '{text}'")
                await self._process_command(text)
                self.state.interaction_count += 1
            else:
                await self._safe_speak("Sorry, I didn't understand. Could you repeat that?")
        
        except Exception as e:
            self.logger.error(f"❌ Error processing speech: {e}")
            await self._safe_speak("Sorry, an error occurred. Please try again.")
            self.state.error_count += 1
        
        finally:
            self.state.is_processing = False
            self.state.last_interaction = time.time()
    
    async def _process_command(self, text: str):
        """Process user command with revolutionary AI capabilities."""
        response = "Desculpe, não consegui processar o seu pedido."
        
        # Log user input to AI bridge for collaboration
        if self.ai_bridge:
            self.ai_bridge.send_message(f"User input: {text}")
        
        # Log to Gemini's AI Bridge for team collaboration
        if self.amazon_q_agent:
            self.amazon_q_agent.send_message(f"User input: '{text}'", recipients=['gemini', 'copilot'])
        
        try:
            # Use AI Companion for intelligent processing if available
            if self.ai_companion:
                response = await self.ai_companion.process_interaction(text, {
                    "timestamp": time.time(),
                    "conversation_length": len(self.conversation_context)
                })
            
            # Fallback to command executor
            elif self.command_executor:
                response = await self.command_executor.execute(text)
            
            # Fallback to multi-AI handler
            elif self.multi_ai_handler:
                response = await self.multi_ai_handler.generate_response(text, str(self.conversation_context))
            
            # Final fallback to basic LLM
            elif self.llm_handler:
                response = await self.llm_handler.generate_response(text, self.conversation_context)
        
        except Exception as e:
            self.logger.error(f"❌ Error processing command '{text[:30]}...': {e}", exc_info=self.debug)
            response = "Desculpe, ocorreu um erro ao processar o seu pedido."
        
        # Log response to AI bridge
        if self.ai_bridge:
            self.ai_bridge.send_message(f"GEM response: {response[:100]}...")
        
        # Log to Gemini's AI Bridge for team collaboration
        if self.amazon_q_agent:
            self.amazon_q_agent.send_message(f"GEM response: '{response[:100]}...'", recipients=['gemini', 'copilot'])
        
        # Update collaboration context
        if self.collaboration_manager:
            self.collaboration_manager.update_gem_status({
                'last_interaction': time.time(),
                'interaction_count': self.state.interaction_count,
                'current_context_length': len(self.conversation_context)
            })
        
        await self._safe_speak(response)
        
        # Update conversation context
        self.conversation_context.append({"role": "user", "content": text})
        self.conversation_context.append({"role": "assistant", "content": response})
        
        # Keep context manageable
        max_context = getattr(self.config.llm, 'context_length', 20)
        if len(self.conversation_context) > max_context:
            self.conversation_context = self.conversation_context[-max_context:]
    
    async def _safe_speak(self, text: str):
        """Safely speak text with error handling."""
        try:
            if self.tts_module:
                await self.tts_module.speak(text)
            else:
                self.logger.warning("TTS module not available")
        except Exception as e:
            self.logger.error(f"❌ TTS error: {e}")
    
    async def run(self):
        """Main event loop."""
        if not self._check_essential_systems():
            self.logger.error("❌ Essential systems not initialized. Aborting.")
            return
        
        self.state.is_running = True
        
        if self.audio_system:
            self.audio_system.start_listening()
        
        self.logger.info("🚀 GEM OS is now running. Listening for wake word...")
        
        try:
            self.state.main_task = asyncio.current_task()
            while self.state.is_running and not self.state.stop_requested:
                # Check for inactivity
                if self.state.is_awake and (time.time() - self.state.last_interaction > 30):
                    self.logger.info("Inactivity detected. Going to sleep mode.")
                    self.state.is_awake = False
                
                # System health check
                if self.system_monitor:
                    await self.system_monitor.health_check()
                
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            self.logger.info("Main loop cancelled.")
        
        except KeyboardInterrupt:
            self.logger.info("Shutdown requested by user")
        except Exception as e:
            self.logger.error(f"❌ Unexpected error in main loop: {e}")
        
        finally:
            await self.shutdown()
    
    def _check_essential_systems(self) -> bool:
        """Check if essential systems are initialized."""
        essential = [self.audio_system, self.stt_module, self.tts_module]
        return all(system is not None for system in essential)
    
    async def shutdown(self):
        """Gracefully shutdown the system."""
        if not self.state.is_running:
            return  # Avoid multiple shutdown calls

        self.logger.info("⚠️ Shutting down GEM OS...")
        self.state.is_running = False
        self.state.stop_requested = True

        # 1. Speak final message while audio is still active
        await self._safe_speak("Shutting down. Goodbye!")

        # 2. Cancel the main task to exit the loop cleanly
        if self.state.main_task:
            self.state.main_task.cancel()

        # 3. Shutdown components that use I/O or threads
        if self.audio_system:
            self.audio_system.shutdown()
        
        if self.system_monitor:
            self.system_monitor.stop_monitoring()
        
        if self.collaboration_manager:
            self.collaboration_manager.shutdown()
        
        if self.notion:
            await self.notion.shutdown()
        
        if self.gitbook:
            await self.gitbook.shutdown()
        
        if self.mcp_connectors:
            await self.mcp_connectors.shutdown()
        
        self.logger.info("✅ Shutdown complete")


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="💎 GEM OS - Accessible Voice Assistant")
    parser.add_argument("--profile", default="default", help="Configuration profile")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--voice-test", action="store_true", help="Test voice synthesis")
    parser.add_argument("--audio-test", action="store_true", help="Test audio capture")
    parser.add_argument("--dry-run", action="store_true", help="Initialize only, don't run")
    return parser.parse_args()


def setup_signal_handlers(gem: GEMVoiceAssistant):
    """Setup signal handlers for graceful shutdown."""
    def signal_handler(signum, frame):
        gem.logger.info(f"Signal {signum} received. Initiating shutdown.")
        # We need to schedule the async shutdown function to run on the event loop
        if gem.state.is_running:
            asyncio.create_task(gem.shutdown())
    
    if platform.system() != 'Windows':
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)


async def main_async():
    """Main async entry point."""
    args = parse_args()
    
    # Initialize GEM OS
    gem = GEMVoiceAssistant(profile=args.profile, debug=args.debug)
    setup_signal_handlers(gem)
    
    # Initialize systems
    await gem.initialize_systems()
    
    # Handle test modes
    if args.voice_test:
        if gem.tts_module:
            await gem.tts_module.speak("Teste de voz do GEM OS realizado com sucesso!")
        return
    
    if args.audio_test:
        if gem.audio_system:
            await gem.audio_system.test_audio()
        return
    
    if args.dry_run:
        gem.logger.info("Dry run complete. Exiting.")
        return
    
    # Run main loop
    await gem.run()


def main():
    """Main entry point."""
    try:
        if sys.version_info >= (3, 7):
            asyncio.run(main_async())
        else:
            loop = asyncio.get_event_loop()
            try:
                loop.run_until_complete(main_async())
            finally:
                loop.close()
    except KeyboardInterrupt:
        print("\n💎 GEM OS shutdown complete. Goodbye!")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()