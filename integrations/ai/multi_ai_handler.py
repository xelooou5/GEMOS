#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
💎 GEM OS - Multi-AI Handler
Integrating multiple AI providers for enhanced capabilities
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod


class AIProvider(ABC):
    """Base class for AI providers."""
    
    def __init__(self, config: Dict[str, Any], logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.is_available = False
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the AI provider."""
        pass
    
    @abstractmethod
    async def generate_response(self, prompt: str, context: str = "") -> str:
        """Generate response from the AI provider."""
        pass


class GitHubCopilotProvider(AIProvider):
    """GitHub Copilot integration for code generation."""
    
    async def initialize(self) -> bool:
        """Initialize GitHub Copilot."""
        try:
            api_key = self.config.get('api_key')
            if api_key and api_key != "your_github_copilot_key_here":
                self.is_available = True
                self.logger.info("GitHub Copilot initialized")
                return True
            return False
        except Exception as e:
            self.logger.error(f"GitHub Copilot initialization failed: {e}")
            return False
    
    async def generate_response(self, prompt: str, context: str = "") -> str:
        """Generate code or technical responses."""
        if not self.is_available:
            return "GitHub Copilot não disponível"
        
        if any(keyword in prompt.lower() for keyword in ['código', 'programar', 'função', 'script']):
            return f"GitHub Copilot: Aqui está uma sugestão de código para '{prompt}'. [Código seria gerado aqui]"
        
        return "GitHub Copilot é especializado em geração de código."


class GeminiProvider(AIProvider):
    """Google Gemini integration for educational content."""
    
    async def initialize(self) -> bool:
        """Initialize Google Gemini."""
        try:
            api_key = self.config.get('api_key')
            if api_key and api_key != "your_gemini_api_key_here":
                self.is_available = True
                self.logger.info("Google Gemini initialized")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Google Gemini initialization failed: {e}")
            return False
    
    async def generate_response(self, prompt: str, context: str = "") -> str:
        """Generate educational content."""
        if not self.is_available:
            return "Google Gemini não disponível"
        
        if any(keyword in prompt.lower() for keyword in ['ensinar', 'aprender', 'explicar', 'educação']):
            return f"Gemini: '{prompt}' é um tópico fascinante. Vou explicar de forma simples e acessível..."
        
        return "Google Gemini é especializado em conteúdo educacional."


class MultiAIHandler:
    """Multi-AI provider handler with intelligent routing."""
    
    def __init__(self, config, logger: Optional[logging.Logger] = None):
        self.config = config
        self.logger = logger or logging.getLogger("MultiAIHandler")
        
        self.providers: Dict[str, AIProvider] = {}
        self.provider_priority = ['gemini', 'github_copilot']
        
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialize AI providers."""
        try:
            ai_config = getattr(self.config, 'ai_providers', {})
            
            if hasattr(ai_config, 'github_copilot') and ai_config.github_copilot.get('enabled', False):
                self.providers['github_copilot'] = GitHubCopilotProvider(
                    ai_config.github_copilot, self.logger
                )
            
            if hasattr(ai_config, 'gemini') and ai_config.gemini.get('enabled', False):
                self.providers['gemini'] = GeminiProvider(
                    ai_config.gemini, self.logger
                )
        except Exception as e:
            self.logger.error(f"Error initializing providers: {e}")
    
    async def initialize(self):
        """Initialize all available providers."""
        self.logger.info("Initializing multi-AI handler...")
        
        for name, provider in self.providers.items():
            try:
                success = await provider.initialize()
                if success:
                    self.logger.info(f"✅ {name} initialized")
                else:
                    self.logger.warning(f"⚠️ {name} failed")
            except Exception as e:
                self.logger.error(f"❌ {name} error: {e}")
        
        available = len(self.get_available_providers())
        self.logger.info(f"Multi-AI handler initialized with {available} providers")
    
    def get_available_providers(self) -> List[str]:
        """Get list of available providers."""
        return [name for name, provider in self.providers.items() if provider.is_available]
    
    async def generate_response(self, prompt: str, context: str = "") -> str:
        """Generate response using best available provider."""
        best_provider = self._select_best_provider(prompt)
        
        if not best_provider:
            return "Nenhum provedor de IA disponível."
        
        try:
            response = await self.providers[best_provider].generate_response(prompt, context)
            return response
        except Exception as e:
            self.logger.error(f"Error with {best_provider}: {e}")
            return "Erro ao gerar resposta."
    
    def _select_best_provider(self, prompt: str) -> Optional[str]:
        """Select best provider for prompt."""
        prompt_lower = prompt.lower()
        
        if any(keyword in prompt_lower for keyword in ['código', 'programar', 'função']):
            if 'github_copilot' in self.providers and self.providers['github_copilot'].is_available:
                return 'github_copilot'
        
        elif any(keyword in prompt_lower for keyword in ['ensinar', 'aprender', 'explicar']):
            if 'gemini' in self.providers and self.providers['gemini'].is_available:
                return 'gemini'
        
        for provider_name in self.provider_priority:
            if provider_name in self.providers and self.providers[provider_name].is_available:
                return provider_name
        
        return None