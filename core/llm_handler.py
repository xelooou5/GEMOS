#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
💎 GEM OS - LLM Handler
AI integration with multiple providers and accessibility focus
"""

import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union
import aiohttp


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    def __init__(self, config: Dict[str, Any], logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.is_initialized = False
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the LLM provider."""
        pass
    
    @abstractmethod
    async def generate_response(self, prompt: str, context: List[Dict[str, Any]] = None) -> str:
        """Generate response from the LLM."""
        pass
    
    @abstractmethod
    def shutdown(self):
        """Shutdown the LLM provider."""
        pass


class OllamaProvider(LLMProvider):
    """Ollama LLM provider for local AI models."""
    
    def __init__(self, config: Dict[str, Any], logger: logging.Logger):
        super().__init__(config, logger)
        self.base_url = config.get('base_url', 'http://localhost:11434')
        self.model = config.get('model', 'phi3:mini')
        self.session = None
    
    async def initialize(self) -> bool:
        """Initialize Ollama connection."""
        try:
            self.session = aiohttp.ClientSession()
            
            # Test connection
            async with self.session.get(f"{self.base_url}/api/tags") as response:
                if response.status == 200:
                    models = await response.json()
                    model_names = [model['name'] for model in models.get('models', [])]
                    
                    if self.model in model_names:
                        self.is_initialized = True
                        self.logger.info(f"Ollama initialized with model: {self.model}")
                        return True
                    else:
                        self.logger.error(f"Model '{self.model}' not found in Ollama")
                        return False
                else:
                    self.logger.error(f"Ollama connection failed: {response.status}")
                    return False
        
        except Exception as e:
            self.logger.error(f"Error initializing Ollama: {e}")
            return False
    
    async def generate_response(self, prompt: str, context: List[Dict[str, Any]] = None) -> str:
        """Generate response using Ollama."""
        if not self.is_initialized:
            return "Desculpe, o sistema de IA não está disponível no momento."
        
        try:
            # Build messages
            messages = []
            
            # Add system prompt
            system_prompt = self.config.get('system_prompt', 
                "Você é o GEM, um assistente de voz acessível e amigável. "
                "Responda de forma clara, concisa e útil. "
                "Foque em ajudar pessoas com necessidades especiais.")
            
            messages.append({"role": "system", "content": system_prompt})
            
            # Add context if provided
            if context:
                for msg in context[-10:]:  # Keep last 10 messages
                    messages.append(msg)
            
            # Add current prompt
            messages.append({"role": "user", "content": prompt})
            
            # Prepare request
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": self.config.get('temperature', 0.7),
                    "top_p": 0.9,
                    "top_k": 40,
                    "num_predict": self.config.get('max_tokens', 1000)
                }
            }
            
            # Make request
            async with self.session.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    return result.get('message', {}).get('content', 
                        "Desculpe, não consegui gerar uma resposta.")
                else:
                    self.logger.error(f"Ollama request failed: {response.status}")
                    return "Desculpe, ocorreu um erro ao processar sua solicitação."
        
        except asyncio.TimeoutError:
            self.logger.error("Ollama request timeout")
            return "Desculpe, a resposta está demorando muito. Tente novamente."
        
        except Exception as e:
            self.logger.error(f"Ollama generation error: {e}")
            return "Desculpe, ocorreu um erro ao gerar a resposta."
    
    def shutdown(self):
        """Shutdown Ollama provider."""
        if self.session:
            asyncio.create_task(self.session.close())
        self.is_initialized = False


class OpenAIProvider(LLMProvider):
    """OpenAI LLM provider."""
    
    def __init__(self, config: Dict[str, Any], logger: logging.Logger):
        super().__init__(config, logger)
        self.api_key = config.get('api_key')
        self.model = config.get('model', 'gpt-3.5-turbo')
        self.session = None
    
    async def initialize(self) -> bool:
        """Initialize OpenAI connection."""
        if not self.api_key:
            self.logger.error("OpenAI API key not provided")
            return False
        
        try:
            self.session = aiohttp.ClientSession(
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
            
            # Test connection
            async with self.session.get("https://api.openai.com/v1/models") as response:
                if response.status == 200:
                    self.is_initialized = True
                    self.logger.info(f"OpenAI initialized with model: {self.model}")
                    return True
                else:
                    self.logger.error(f"OpenAI connection failed: {response.status}")
                    return False
        
        except Exception as e:
            self.logger.error(f"Error initializing OpenAI: {e}")
            return False
    
    async def generate_response(self, prompt: str, context: List[Dict[str, Any]] = None) -> str:
        """Generate response using OpenAI."""
        if not self.is_initialized:
            return "Desculpe, o sistema de IA não está disponível no momento."
        
        try:
            # Build messages
            messages = []
            
            # Add system prompt
            system_prompt = self.config.get('system_prompt',
                "You are GEM, an accessible and friendly voice assistant. "
                "Respond clearly, concisely, and helpfully. "
                "Focus on helping people with special needs. Respond in Portuguese.")
            
            messages.append({"role": "system", "content": system_prompt})
            
            # Add context if provided
            if context:
                for msg in context[-10:]:  # Keep last 10 messages
                    messages.append(msg)
            
            # Add current prompt
            messages.append({"role": "user", "content": prompt})
            
            # Prepare request
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": self.config.get('temperature', 0.7),
                "max_tokens": self.config.get('max_tokens', 1000),
                "top_p": 0.9,
                "frequency_penalty": 0.0,
                "presence_penalty": 0.0
            }
            
            # Make request
            async with self.session.post(
                "https://api.openai.com/v1/chat/completions",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    return result['choices'][0]['message']['content']
                else:
                    self.logger.error(f"OpenAI request failed: {response.status}")
                    return "Desculpe, ocorreu um erro ao processar sua solicitação."
        
        except asyncio.TimeoutError:
            self.logger.error("OpenAI request timeout")
            return "Desculpe, a resposta está demorando muito. Tente novamente."
        
        except Exception as e:
            self.logger.error(f"OpenAI generation error: {e}")
            return "Desculpe, ocorreu um erro ao gerar a resposta."
    
    def shutdown(self):
        """Shutdown OpenAI provider."""
        if self.session:
            asyncio.create_task(self.session.close())
        self.is_initialized = False


class LocalProvider(LLMProvider):
    """Local LLM provider using transformers."""
    
    def __init__(self, config: Dict[str, Any], logger: logging.Logger):
        super().__init__(config, logger)
        self.model = None
        self.tokenizer = None
        self.model_name = config.get('model', 'microsoft/DialoGPT-medium')
    
    async def initialize(self) -> bool:
        """Initialize local model."""
        try:
            from transformers import AutoTokenizer, AutoModelForCausalLM
            import torch
            
            self.logger.info(f"Loading local model: {self.model_name}")
            
            # Load in executor to avoid blocking
            loop = asyncio.get_event_loop()
            
            self.tokenizer = await loop.run_in_executor(
                None, AutoTokenizer.from_pretrained, self.model_name
            )
            
            self.model = await loop.run_in_executor(
                None, AutoModelForCausalLM.from_pretrained, self.model_name
            )
            
            # Set pad token if not exists
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            self.is_initialized = True
            self.logger.info("Local model initialized")
            return True
        
        except ImportError:
            self.logger.error("transformers library not available")
            return False
        except Exception as e:
            self.logger.error(f"Error initializing local model: {e}")
            return False
    
    async def generate_response(self, prompt: str, context: List[Dict[str, Any]] = None) -> str:
        """Generate response using local model."""
        if not self.is_initialized:
            return "Desculpe, o sistema de IA não está disponível no momento."
        
        try:
            import torch
            
            # Prepare input
            input_text = prompt
            if context:
                # Add some context
                recent_context = context[-3:]  # Last 3 messages
                context_text = " ".join([msg.get('content', '') for msg in recent_context])
                input_text = f"{context_text} {prompt}"
            
            # Tokenize
            inputs = self.tokenizer.encode(input_text, return_tensors='pt')
            
            # Generate in executor
            loop = asyncio.get_event_loop()
            outputs = await loop.run_in_executor(
                None, self._generate_sync, inputs
            )
            
            # Decode response
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # Extract new part (remove input)
            if len(response) > len(input_text):
                response = response[len(input_text):].strip()
            
            return response if response else "Desculpe, não consegui gerar uma resposta."
        
        except Exception as e:
            self.logger.error(f"Local generation error: {e}")
            return "Desculpe, ocorreu um erro ao gerar a resposta."
    
    def _generate_sync(self, inputs):
        """Synchronous generation method."""
        import torch
        
        with torch.no_grad():
            outputs = self.model.generate(
                inputs,
                max_length=inputs.shape[1] + 100,
                num_return_sequences=1,
                temperature=self.config.get('temperature', 0.7),
                do_sample=True,
                pad_token_id=self.tokenizer.pad_token_id
            )
        
        return outputs
    
    def shutdown(self):
        """Shutdown local provider."""
        self.model = None
        self.tokenizer = None
        self.is_initialized = False


class LLMHandler:
    """Main LLM handler with multiple provider support."""
    
    def __init__(self, config, logger: Optional[logging.Logger] = None):
        self.config = config
        self.logger = logger or logging.getLogger("LLMHandler")
        
        self.providers: Dict[str, LLMProvider] = {}
        self.current_provider: Optional[LLMProvider] = None
        self.fallback_providers: List[str] = []
        
        # Response cache
        self.response_cache: Dict[str, str] = {}
        self.cache_max_size = 100
    
    async def initialize(self):
        """Initialize LLM providers."""
        self.logger.info("Initializing LLM handler...")
        
        # Define available providers
        provider_classes = {
            'ollama': OllamaProvider,
            'openai': OpenAIProvider,
            'local': LocalProvider
        }
        
        primary_provider = self.config.provider
        
        # Initialize primary provider
        if primary_provider in provider_classes:
            provider_class = provider_classes[primary_provider]
            provider = provider_class(self.config.__dict__, self.logger)
            
            if await provider.initialize():
                self.providers[primary_provider] = provider
                self.current_provider = provider
                self.logger.info(f"Primary LLM provider '{primary_provider}' initialized")
            else:
                self.logger.warning(f"Failed to initialize primary provider '{primary_provider}'")
        
        # Initialize fallback providers
        for provider_name, provider_class in provider_classes.items():
            if provider_name != primary_provider and provider_name not in self.providers:
                provider = provider_class(self.config.__dict__, self.logger)
                
                if await provider.initialize():
                    self.providers[provider_name] = provider
                    self.fallback_providers.append(provider_name)
                    self.logger.info(f"Fallback LLM provider '{provider_name}' initialized")
        
        if not self.current_provider:
            if self.fallback_providers:
                self.current_provider = self.providers[self.fallback_providers[0]]
                self.logger.info(f"Using fallback provider: {self.fallback_providers[0]}")
            else:
                self.logger.warning("No LLM providers could be initialized")
        
        self.logger.info("LLM handler initialization complete")
    
    async def generate_response(self, prompt: str, context: List[Dict[str, Any]] = None) -> str:
        """Generate AI response."""
        if not self.current_provider:
            return self._get_fallback_response(prompt)
        
        # Check cache first
        cache_key = self._get_cache_key(prompt, context)
        if cache_key in self.response_cache:
            self.logger.debug("Using cached response")
            return self.response_cache[cache_key]
        
        # Try current provider
        response = await self.current_provider.generate_response(prompt, context)
        
        # If current provider fails, try fallbacks
        if not response or "desculpe" in response.lower():
            if self.fallback_providers:
                self.logger.warning("Primary LLM provider failed, trying fallbacks")
                
                for fallback_name in self.fallback_providers:
                    if fallback_name in self.providers:
                        self.logger.info(f"Trying fallback LLM provider: {fallback_name}")
                        fallback_provider = self.providers[fallback_name]
                        response = await fallback_provider.generate_response(prompt, context)
                        
                        if response and "desculpe" not in response.lower():
                            self.logger.info(f"Fallback provider '{fallback_name}' succeeded")
                            break
        
        # If all providers fail, use fallback response
        if not response or "desculpe" in response.lower():
            response = self._get_fallback_response(prompt)
        
        # Cache response
        self._cache_response(cache_key, response)
        
        # Post-process response
        response = self._post_process_response(response)
        
        return response
    
    def _get_fallback_response(self, prompt: str) -> str:
        """Get fallback response when AI is not available."""
        prompt_lower = prompt.lower()
        
        # Simple pattern matching for common queries
        if any(word in prompt_lower for word in ['olá', 'oi', 'hello', 'hi']):
            return "Olá! Como posso ajudar você hoje?"
        
        elif any(word in prompt_lower for word in ['como', 'what', 'que']):
            return "Posso ajudar com informações, lembretes, acessibilidade e muito mais. O que você gostaria de saber?"
        
        elif any(word in prompt_lower for word in ['obrigado', 'thanks', 'valeu']):
            return "De nada! Estou aqui para ajudar sempre que precisar."
        
        elif any(word in prompt_lower for word in ['tchau', 'bye', 'adeus']):
            return "Até logo! Foi um prazer ajudar você."
        
        else:
            return "Desculpe, não tenho acesso ao sistema de IA no momento, mas estou aqui para ajudar com comandos básicos."
    
    def _get_cache_key(self, prompt: str, context: List[Dict[str, Any]] = None) -> str:
        """Generate cache key for response."""
        import hashlib
        
        key_data = prompt
        if context:
            key_data += str(context[-3:])  # Include last 3 context messages
        
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _cache_response(self, key: str, response: str):
        """Cache response with size limit."""
        if len(self.response_cache) >= self.cache_max_size:
            # Remove oldest entry
            oldest_key = next(iter(self.response_cache))
            del self.response_cache[oldest_key]
        
        self.response_cache[key] = response
    
    def _post_process_response(self, response: str) -> str:
        """Post-process AI response."""
        # Clean up response
        response = response.strip()
        
        # Remove common AI disclaimers that might confuse users
        disclaimers = [
            "Como um assistente de IA,",
            "Como uma IA,",
            "Eu sou uma IA e",
            "Como modelo de linguagem,"
        ]
        
        for disclaimer in disclaimers:
            if response.startswith(disclaimer):
                response = response[len(disclaimer):].strip()
        
        # Ensure response is not too long for speech
        max_length = 500
        if len(response) > max_length:
            # Find last complete sentence within limit
            sentences = response.split('.')
            truncated = ""
            for sentence in sentences:
                if len(truncated + sentence + '.') <= max_length:
                    truncated += sentence + '.'
                else:
                    break
            
            if truncated:
                response = truncated
            else:
                response = response[:max_length] + "..."
        
        return response
    
    def switch_provider(self, provider_name: str) -> bool:
        """Switch to a different LLM provider."""
        if provider_name in self.providers:
            self.current_provider = self.providers[provider_name]
            self.logger.info(f"Switched to LLM provider: {provider_name}")
            return True
        else:
            self.logger.error(f"LLM provider '{provider_name}' not available")
            return False
    
    def get_available_providers(self) -> List[str]:
        """Get list of available providers."""
        return list(self.providers.keys())
    
    def get_current_provider(self) -> Optional[str]:
        """Get current provider name."""
        for name, provider in self.providers.items():
            if provider == self.current_provider:
                return name
        return None
    
    def clear_cache(self):
        """Clear response cache."""
        self.response_cache.clear()
        self.logger.info("Response cache cleared")
    
    async def test_generation(self, test_prompt: str = "Olá, como você está?"):
        """Test LLM generation."""
        self.logger.info("Testing LLM generation...")
        
        response = await self.generate_response(test_prompt)
        
        self.logger.info(f"Test prompt: {test_prompt}")
        self.logger.info(f"Test response: {response}")
        
        return response
    
    def shutdown(self):
        """Shutdown all LLM providers."""
        self.logger.info("Shutting down LLM handler...")
        
        for provider in self.providers.values():
            provider.shutdown()
        
        self.providers.clear()
        self.current_provider = None
        self.fallback_providers.clear()
        self.response_cache.clear()
        
        self.logger.info("LLM handler shutdown complete")