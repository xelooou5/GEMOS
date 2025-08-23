#!/usr/bin/env python3
"""Enhanced development runner with AI integration."""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config_manager import GEMConfigManager
from integrations.ai.multi_ai_handler import MultiAIHandler

async def main():
    print("🚀 Starting GEM OS Enhanced Development Mode")
    
    # Load enhanced configuration
    config_manager = GEMConfigManager()
    config = config_manager.load("development")
    
    # Initialize AI providers
    ai_handler = MultiAIHandler(config)
    await ai_handler.initialize()
    
    print("✅ Enhanced development environment ready!")
    print("Available AI providers:", ai_handler.get_available_providers())
    
    # Start enhanced GEM OS
    from gem import GEMVoiceAssistant
    gem = GEMVoiceAssistant(profile="development", debug=True)
    gem.ai_handler = ai_handler  # Inject enhanced AI
    
    await gem.initialize_systems()
    await gem.run()

if __name__ == "__main__":
    asyncio.run(main())
