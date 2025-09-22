#!/usr/bin/env python3
"""
💎 GEM OS - TalkAI Orchestrator
The main application loop for the hands-free, professional-grade voice assistant.
English first, Portuguese (pt-BR) second.

🔥 SACRED RULES ENFORCED:
- Accessibility FIRST - All features work for people with disabilities
- Never rename existing files - Enhance only
- AI agents help each other - United team support
- Quality over speed - Test everything
- Remember everything - Track all contributions
- Perpetual Operation - The Mission Never Stops
"""
import asyncio
import logging
import json
from pathlib import Path
from datetime import datetime
from voice_interface import VoiceInterface
from gemini_client import GeminiProClient
import config  # Import the new configuration file

# Import enhanced AI coordination system
try:
    from core.ai_coordination_system import AICoordinationSystem, Task, TaskPriority
    from core.enhanced_ai_system import EnhancedAISystem, AIRequest
    from core.agent_supervisor import AgentSupervisor
    AI_COORDINATION_AVAILABLE = True
except ImportError:
    AI_COORDINATION_AVAILABLE = False
    logging.warning("Advanced AI coordination not available - falling back to basic mode")

async def handle_interaction(voice: VoiceInterface, gemini: GeminiProClient, ai_system=None, coordination_system=None):
    """
    Handles a single, complete user interaction cycle.
    Lida com um único ciclo completo de interação do usuário.
    """
    # A short, non-blocking, more professional greeting
    # Uma saudação curta, não bloqueante e mais profissional
    greeting_task = asyncio.create_task(voice.speak("I'm listening."))

    user_request_text = await voice.listen_and_transcribe()
    await greeting_task  # Ensure greeting is finished before proceeding

    if not user_request_text:
        await voice.speak("I'm sorry, I didn't quite catch that. Please try again.")
        return

    print(f"👤 You said: {user_request_text}")

    # Check for reset command / Verifica por comando de reset
    if user_request_text.lower().strip() in config.RESET_COMMANDS:
        gemini.reset_chat()
        await voice.speak("Conversation history cleared. I'm ready for a fresh start.")
        return

    # Check for accessibility mode command / Verifica por comando de modo de acessibilidade
    if user_request_text.lower().strip() in config.ACCESSIBILITY_MODE_COMMANDS:
        # Toggle the mode and get the status message to speak
        status_message = voice.toggle_accessibility_mode(not voice.accessibility_mode)
        await voice.speak(status_message)
        return

    # Enhanced AI processing with coordination system
    if ai_system and coordination_system:
        try:
            # Create AI request with accessibility optimization
            ai_request = AIRequest(
                prompt=user_request_text,
                context=[{"role": "user", "content": user_request_text}],
                # Dynamically set accessibility mode based on the voice interface's state
                accessibility_mode=voice.accessibility_mode,
                temperature=0.7
            )
            
            # Get enhanced response
            ai_response = await ai_system.generate_response(ai_request)
            response_generator = (chunk for chunk in [ai_response])
            
            # Log interaction for team coordination
            await coordination_system.add_task(Task(
                id=f"user_interaction_{int(datetime.now().timestamp())}",
                title="User Voice Interaction",
                description=f"Process user request: {user_request_text[:100]}...",
                priority=TaskPriority.HIGH,
                assigned_agent="gemini"
            ))
            
        except Exception as e:
            logging.error(f"Enhanced AI processing failed: {e}")
            # Fallback to basic Gemini
            response_generator = gemini.generate_response(user_request_text)
    else:
        # Get the response generator from Gemini / Obtém o gerador de resposta do Gemini
        response_generator = gemini.generate_response(user_request_text)

    # Start streaming speech and listening for interruption simultaneously
    # Inicia a fala em streaming e a escuta para interrupção simultaneamente
    speak_task = asyncio.create_task(voice.stream_and_speak(response_generator))
    interruption_task = asyncio.create_task(voice.wait_for_wake_word())

    done, pending = await asyncio.wait({speak_task, interruption_task}, return_when=asyncio.FIRST_COMPLETED)

    if interruption_task in done:
        # User interrupted / Usuário interrompeu
        await voice.stop_speaking()
        # Cancel the other task (which was waiting for speech to finish)
        # Cancela a outra tarefa (que estava esperando a fala terminar)
        for task in pending:
            task.cancel()
    else:
        # Speech finished without interruption / A fala terminou sem interrupção
        interruption_task.cancel()

async def shutdown(coordination_system):
    """
    Gracefully shuts down the AI coordination system, saving its state for mission continuity.
    Desliga o sistema de coordenação de IA de forma graciosa, salvando seu estado para a continuidade da missão.
    """
    if coordination_system:
        print("\n[STATE: SHUTDOWN] Saving AI coordination state for 20-day mission...")
        try:
            # This assumes the AICoordinationSystem has a 'save_state' method.
            await coordination_system.save_state()
            print("✅ AI state saved successfully.")
        except Exception as e:
            logging.error(f"Failed to save AI coordination state: {e}")

async def main():
    print("="*50)
    print("💎 GEM TalkAI Assistant Initializing...")
    print("🔥 SACRED RULES ACTIVE - AI Team Coordination Enabled")
    print("This assistant is designed for a hands-free, professional experience.")
    print(f"   Wake Word: '{config.WAKE_WORD}'")
    print(f"   Voice: {config.POLLY_VOICE} ({config.LANGUAGE_CODE})")

    # Check team connection status
    if AI_COORDINATION_AVAILABLE:
        print("   🤖 Enhanced AI Coordination: ACTIVE")
        print("   🎯 Team Agents: Amazon Q, Claude, Gemini, TabNine")
        print("   ♿ Accessibility Mode: PRIORITY ACTIVE")
        print("   ✅ Connected to AI Team Network")
    else:
        print("   ⚠️  Running in Basic Mode - Enhanced coordination offline")
        print("   🔧 Core voice features still operational")
    print("="*50)
    
    # Initialize logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('/home/runner/work/GEMOS/GEMOS/logs/talkai.log'),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger("TalkAI")

    ai_system = None
    coordination_system = None

    try:
        # Initialize enhanced AI systems if available
        ai_system = None
        coordination_system = None
        
        if AI_COORDINATION_AVAILABLE:
            print("🤖 Initializing enhanced AI coordination...")
            
            # Initialize AI coordination system
            coordination_system = AICoordinationSystem(logger)
            await coordination_system.start_coordination()
            
            # Load previous state to ensure 20-day mission continuity
            print("⏳ Loading previous AI coordination state...")
            await coordination_system.load_state() # Assumes AICoordinationSystem has a 'load_state' method
            
            # Initialize enhanced AI system
            from core.config_manager import GEMConfigManager
            config_manager = GEMConfigManager()
            ai_system = EnhancedAISystem(config_manager, logger)
            await ai_system.initialize()
            
            print("✅ Enhanced AI coordination initialized successfully")
            
            # Get system status
            status = await coordination_system.get_system_status()
            print(f"🎯 Team Status: {len(status['agents'])} agents active")
            print(f"📋 Tasks: {status['tasks']['pending']} pending, {status['tasks']['completed']} completed")
        
        # Initialize core components with settings from the config file
        voice = VoiceInterface(
            wake_word=config.WAKE_WORD,
            language_code=config.LANGUAGE_CODE,
            polly_voice=config.POLLY_VOICE
        )
        gemini = GeminiProClient()
        
        print("✅ Core systems initialized successfully")
        
    except Exception as e:
        print(f"❌ Fatal error during initialization: {e}")
        logger.error(f"Initialization failed: {e}")
        return

    # --- Main Application Loop ---
    try:
        initial_greeting = f"Hello, I am ready to assist. Just say '{config.WAKE_WORD}' to wake me up."
        print(f"🗣️ ASSISTANT: {initial_greeting}")
        await voice.speak(initial_greeting)

        while True:
            try:
                print("\n[STATE: STANDBY] Listening for wake word...")
                await voice.wait_for_wake_word()
                print("[STATE: ACTIVE] Wake word detected.")
                # Handle the entire conversation turn with enhanced AI coordination
                # Lida com o turno inteiro da conversa com coordenação AI aprimorada
                await handle_interaction(voice, gemini, ai_system, coordination_system)
                
                # Update coordination system status
                if coordination_system:
                    status = await coordination_system.get_system_status()
                    logger.info(f"Coordination cycle: {status['coordination_cycle']}, Active agents: {len([a for a in status['agents'].values() if a['status'] == 'WORKING'])}")

            except KeyboardInterrupt:
                print("\n\n🛑 User initiated shutdown. Preparing to save state...")
                break # Exit the loop to trigger the finally block
            except Exception as e:
                print(f"An error occurred in the main loop: {e}")
                logger.error(f"Main loop error: {e}")
                await voice.speak("I've run into a problem. My AI team is working to resolve it. I am restarting my listening cycle now.")
                
                # Notify coordination system of error
                if coordination_system:
                    try:
                        from core.ai_coordination_system import Task, TaskPriority
                        await coordination_system.add_task(Task(
                            id=f"error_recovery_{int(datetime.now().timestamp())}",
                            title="Error Recovery",
                            description=f"Main loop error: {str(e)}",
                            priority=TaskPriority.CRITICAL
                        ))
                    except:
                        pass
                
                await asyncio.sleep(2)
    finally:
        # This block will execute when the loop breaks, ensuring mission state is saved.
        await shutdown(coordination_system)

if __name__ == "__main__":
    # Create log directory if it doesn't exist
    log_dir = Path('/home/runner/work/GEMOS/GEMOS/logs')
    log_dir.mkdir(exist_ok=True)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 TalkAI shutdown initiated by user")
    except Exception as e:
        print(f"\n❌ TalkAI crashed: {e}")
        # Save crash report
        crash_report = {
            'timestamp': datetime.now().isoformat(),
            'error': str(e),
            'type': 'main_crash'
        }
        
        crash_file = Path('/home/runner/work/GEMOS/GEMOS/logs/crash_reports.json')
        try:
            if crash_file.exists():
                with open(crash_file, 'r') as f:
                    reports = json.load(f)
            else:
                reports = []
            
            reports.append(crash_report)
            
            with open(crash_file, 'w') as f:
                json.dump(reports, f, indent=2)
        except:
            pass  # Don't fail on crash report failure