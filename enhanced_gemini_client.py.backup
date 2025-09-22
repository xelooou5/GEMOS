#!/usr/bin/env python3
"""
💎 GEM OS - Enhanced Gemini Pro Client
Advanced Gemini Pro integration with database caching, context awareness,
and browser-like functionality for superior responses.
"""
import os
import google.generativeai as genai
import sqlite3
import json
import hashlib
from typing import List, Dict, Optional, Any
import time
import asyncio
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
import logging

class EnhancedGeminiClient:
    """Enhanced Gemini Pro client with advanced features."""
    
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_AI_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_AI_API_KEY environment variable not set.")
            
        genai.configure(api_key=self.api_key)
        
        # Use Gemini Pro with advanced configuration
        self.generation_config = {
            'temperature': 0.9,
            'top_k': 40,
            'top_p': 0.95,
            'max_output_tokens': 2048,
        }
        
        self.safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        ]
        
        self.model = genai.GenerativeModel(
            model_name='gemini-pro',
            generation_config=self.generation_config,
            safety_settings=self.safety_settings
        )
        
        # Initialize database for caching and context
        self._init_database()
        
        # Context management
        self.conversation_context = []
        self.max_context_length = 10
        
        # Enhanced system prompt (English first, Portuguese second)
        self.system_prompt = """
You are Gemini, a friendly and professional AI assistant built into the GEM OS.

Core Characteristics:
• Be natural, conversational, and helpful.
• Keep responses concise but complete.
• Use up-to-date and contextual knowledge.
• Adapt to the conversation's tone.
• Be proactive with useful suggestions.
• Demonstrate a friendly yet professional personality.

Advanced Capabilities:
• Access to real-time information.
• Memory of previous conversations.
• Advanced context analysis.
• Integration with the operating system.

You are here to make the user's life easier and more productive.
"""
        
        # Start enhanced chat
        self._init_chat()
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
    def _init_database(self):
        """Initialize SQLite database for caching and context management."""
        self.db_path = '/home/oem/PycharmProjects/gem/gemini_enhanced.db'
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Response cache table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS response_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt_hash TEXT UNIQUE,
                prompt TEXT,
                response TEXT,
                confidence_score REAL,
                tokens_used INTEGER,
                response_time REAL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                expiry_date DATETIME
            )
        ''')
        
        # Conversation history
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                role TEXT,
                content TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                context_tags TEXT
            )
        ''')
        
        # User preferences and learning
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                preference_key TEXT UNIQUE,
                preference_value TEXT,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Knowledge base for enhanced responses
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS knowledge_base (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT,
                content TEXT,
                source TEXT,
                relevance_score REAL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        
    def _init_chat(self):
        """Initialize enhanced chat with system prompt and context."""
        try:
            self.chat = self.model.start_chat(history=[
                {
                    "role": "user",
                    "parts": [self.system_prompt]
                },
                {
                    "role": "model",
                    "parts": ["Perfect! I am Gemini, integrated into the GEM OS, ready to assist. How can I help you today?"]
                }
            ])
        except Exception as e:
            self.logger.error(f"Failed to initialize chat: {e}") # Falha ao inicializar o chat
            self.chat = self.model.start_chat()
            
    def _hash_prompt(self, prompt: str) -> str:
        """Generate hash for prompt caching."""
        return hashlib.md5(prompt.encode('utf-8')).hexdigest()
        
    def _check_cache(self, prompt: str) -> Optional[str]:
        """Check if response is cached and still valid."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            prompt_hash = self._hash_prompt(prompt)
            
            cursor.execute('''
                SELECT response, expiry_date FROM response_cache 
                WHERE prompt_hash = ? AND expiry_date > datetime('now')
            ''', (prompt_hash,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return result[0]
                
        except Exception as e:
            self.logger.error(f"Cache check failed: {e}") # Falha na verificação do cache
            
        return None
        
    def _cache_response(self, prompt: str, response: str, response_time: float, tokens_used: int = 0):
        """Cache response for future use."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            prompt_hash = self._hash_prompt(prompt)
            expiry_date = datetime.now() + timedelta(hours=24)  # Cache for 24 hours
            
            cursor.execute('''
                INSERT OR REPLACE INTO response_cache 
                (prompt_hash, prompt, response, response_time, tokens_used, expiry_date)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (prompt_hash, prompt, response, response_time, tokens_used, expiry_date))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Failed to cache response: {e}") # Falha ao armazenar a resposta no cache
            
    def _store_conversation(self, role: str, content: str, context_tags: List[str] = None):
        """Store conversation in database for context management."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            session_id = f"session_{int(time.time())}"
            tags_json = json.dumps(context_tags or [])
            
            cursor.execute('''
                INSERT INTO conversation_history 
                (session_id, role, content, context_tags)
                VALUES (?, ?, ?, ?)
            ''', (session_id, role, content, tags_json))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Failed to store conversation: {e}") # Falha ao armazenar a conversa
            
    def _enhance_prompt(self, prompt: str) -> str:
        """Enhance prompt with context and user preferences."""
        enhanced_prompt = prompt
        
        # Add recent conversation context
        if self.conversation_context:
            context_str = "\n".join([
                f"{item['role']}: {item['content'][:100]}..."
                for item in self.conversation_context[-3:]
            ])
            enhanced_prompt = f"Recent conversation context:\n{context_str}\n\nCurrent question: {prompt}"
            
        return enhanced_prompt
        
    async def _get_web_context(self, prompt: str) -> str:
        """Get relevant web context for enhanced responses (simulated)."""
        # In a real implementation, this would search the web
        # For now, we'll return empty context
        return ""
        
    def _analyze_prompt_intent(self, prompt: str) -> Dict[str, Any]:
        """Analyze prompt intent for better response optimization."""
        intent_analysis = {
            'type': 'general',
            'complexity': 'medium',
            'requires_web': False,
            'topics': [],
            'urgency': 'normal'
        }
        
        prompt_lower = prompt.lower()
        
        # Detect question types (more language-agnostic)
        if prompt.strip().endswith('?'):
            intent_analysis['type'] = 'question'
            
        # Detect urgency keywords
        if any(word in prompt_lower for word in ['now', 'urgent', 'fast', 'immediately', 'agora', 'urgente', 'rápido']):
            intent_analysis['urgency'] = 'high'
            
        # Detect web search keywords
        if any(word in prompt_lower for word in ['search', 'find', 'look up', 'latest news', 'pesquise', 'procure', 'encontre']):
            intent_analysis['requires_web'] = True
            
        # Detect complexity
        if len(prompt.split()) > 50 or any(word in prompt_lower for word in ['explain in detail', 'complex analysis', 'comparison', 'explique detalhadamente']):
            intent_analysis['complexity'] = 'high'
            
        return intent_analysis
        
    async def generate_enhanced_response(self, prompt: str) -> str:
        """Generate enhanced response with all advanced features."""
        start_time = time.time()
        
        # Check cache first
        cached_response = self._check_cache(prompt)
        if cached_response:
            self.logger.info(f"Cache hit for prompt. Response time: {time.time() - start_time:.2f}s")
            print(f"📦 Using cached response.") # Usando resposta do cache.
            return cached_response
            
        # Analyze prompt intent
        intent = self._analyze_prompt_intent(prompt)
        self.logger.info(f"Intent analysis: {intent}")
        print(f"🧐 Intent: {intent['type']}, Complexity: {intent['complexity']}, Urgency: {intent['urgency']}")
        
        # Enhance prompt with context
        enhanced_prompt = self._enhance_prompt(prompt)
        
        try:            
            print("🧠 Generating enhanced response...") # Gerando resposta aprimorada...
            
            # Adjust generation config based on intent
            if intent['complexity'] == 'high':
                self.model._generation_config.max_output_tokens = 4096
                self.model._generation_config.temperature = 0.7
            elif intent['urgency'] == 'high':
                self.model._generation_config.max_output_tokens = 1024
                self.model._generation_config.temperature = 0.3
                
            # Generate response with streaming
            response = self.chat.send_message(enhanced_prompt, stream=True)
            
            full_response = ""
            print("💬 Streaming response: ", end="") # Resposta em streaming:
            
            for chunk in response:
                if chunk.text:
                    print(chunk.text, end="", flush=True)
                    full_response += chunk.text
                    
            print()  # New line after streaming
            
            # Store conversation context
            self.conversation_context.append({
                'role': 'user',
                'content': prompt,
                'timestamp': datetime.now(),
                'intent': intent
            })
            
            self.conversation_context.append({
                'role': 'assistant',
                'content': full_response,
                'timestamp': datetime.now()
            })
            
            # Keep context manageable
            if len(self.conversation_context) > self.max_context_length:
                self.conversation_context = self.conversation_context[-self.max_context_length:]
                
            response_time = time.time() - start_time
            
            # Cache the response
            self._cache_response(prompt, full_response, response_time)
            
            # Store in database
            self._store_conversation('user', prompt, intent.get('topics', []))
            self._store_conversation('assistant', full_response)
            
            print(f"✅ Response generated in {response_time:.2f}s") # Resposta gerada em {response_time:.2f}s
            
            return full_response
            
        except Exception as e:
            self.logger.error(f"Enhanced response generation failed: {e}")
            print(f"❌ Error during response generation: {e}") # Erro durante a geração da resposta
            
            # Fallback to simple response
            try:
                simple_response = self.chat.send_message(prompt)
                return simple_response.text
            except:
                return "I'm sorry, an error occurred while processing your request. Please try again."
                
    def get_conversation_summary(self) -> str:
        """Get summary of recent conversation."""
        if not self.conversation_context:
            return "No recent conversation." # Nenhuma conversa recente.
            
        summary = "Summary of recent conversation:\n" # Resumo da conversa recente:
        for item in self.conversation_context[-5:]:
            role_emoji = "👤" if item['role'] == 'user' else "🤖"
            content_preview = item['content'][:100] + "..." if len(item['content']) > 100 else item['content']
            summary += f"{role_emoji} {content_preview}\n"
            
        return summary
        
    def clear_context(self):
        """Clear conversation context."""
        self.conversation_context = []
        print("🧽 Conversation context cleared.") # Contexto da conversa limpo.
        
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_queries,
                    AVG(response_time) as avg_response_time,
                    AVG(tokens_used) as avg_tokens,
                    COUNT(CASE WHEN expiry_date > datetime('now') THEN 1 END) as cached_responses
                FROM response_cache
                WHERE timestamp > datetime('now', '-7 days')
            ''')
            
            stats = cursor.fetchone()
            conn.close()
            
            return {
                'total_queries': stats[0] or 0,
                'avg_response_time': round(stats[1] or 0, 2),
                'avg_tokens': int(stats[2] or 0),
                'cached_responses': stats[3] or 0,
                'context_items': len(self.conversation_context)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get performance stats: {e}") # Falha ao obter estatísticas de desempenho
            return {}