#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
💎 GEM OS - AI Companion
Revolutionary AI companion that learns and adapts to each user
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
import sqlite3


@dataclass
class UserProfile:
    """Dynamic user profile that evolves with interaction."""
    user_id: str = "default"
    name: str = ""
    age_group: str = "adult"  # child, teen, adult, elderly
    accessibility_needs: List[str] = None
    learning_style: str = "visual"  # visual, auditory, kinesthetic
    interaction_preferences: Dict[str, Any] = None
    emotional_state: str = "neutral"
    energy_level: int = 5  # 1-10
    stress_level: int = 3  # 1-10
    last_interaction: str = ""
    personality_traits: Dict[str, float] = None
    
    def __post_init__(self):
        if self.accessibility_needs is None:
            self.accessibility_needs = []
        if self.interaction_preferences is None:
            self.interaction_preferences = {}
        if self.personality_traits is None:
            self.personality_traits = {
                "friendliness": 0.8,
                "patience": 0.9,
                "humor": 0.6,
                "formality": 0.4,
                "enthusiasm": 0.7
            }


@dataclass
class EmotionalContext:
    """Emotional context for adaptive responses."""
    detected_emotion: str = "neutral"
    confidence: float = 0.0
    voice_tone: str = "normal"
    response_speed: str = "normal"
    suggested_approach: str = "standard"
    timestamp: str = ""


class EmotionalIntelligence:
    """AI emotional intelligence system."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.emotion_patterns = {
            "frustrated": ["não funciona", "não entendo", "difícil", "complicado"],
            "excited": ["incrível", "fantástico", "adorei", "perfeito"],
            "tired": ["cansado", "exausto", "sono", "descansar"],
            "confused": ["não sei", "como", "ajuda", "explicar"],
            "happy": ["obrigado", "ótimo", "bom", "gostei"],
            "sad": ["triste", "mal", "problema", "difícil"]
        }
    
    async def analyze_emotional_state(self, text: str, voice_features: Dict = None) -> EmotionalContext:
        """Analyze user's emotional state from text and voice."""
        text_lower = text.lower()
        detected_emotions = {}
        
        # Text-based emotion detection
        for emotion, patterns in self.emotion_patterns.items():
            score = sum(1 for pattern in patterns if pattern in text_lower)
            if score > 0:
                detected_emotions[emotion] = score / len(patterns)
        
        # Determine primary emotion
        if detected_emotions:
            primary_emotion = max(detected_emotions, key=detected_emotions.get)
            confidence = detected_emotions[primary_emotion]
        else:
            primary_emotion = "neutral"
            confidence = 0.5
        
        # Generate adaptive response strategy
        approach = self._get_response_approach(primary_emotion)
        
        return EmotionalContext(
            detected_emotion=primary_emotion,
            confidence=confidence,
            suggested_approach=approach,
            timestamp=datetime.now().isoformat()
        )
    
    def _get_response_approach(self, emotion: str) -> str:
        """Get appropriate response approach for emotion."""
        approaches = {
            "frustrated": "patient_supportive",
            "confused": "clear_simple",
            "excited": "enthusiastic_matching",
            "tired": "gentle_brief",
            "sad": "empathetic_caring",
            "happy": "positive_reinforcing"
        }
        return approaches.get(emotion, "standard")


class AdaptivePersonality:
    """Adaptive AI personality that matches user needs."""
    
    def __init__(self, user_profile: UserProfile, logger: logging.Logger):
        self.user_profile = user_profile
        self.logger = logger
    
    def adapt_response_style(self, base_response: str, emotional_context: EmotionalContext) -> str:
        """Adapt response based on user profile and emotional context."""
        
        # Age-appropriate adaptation
        if self.user_profile.age_group == "child":
            base_response = self._make_child_friendly(base_response)
        elif self.user_profile.age_group == "elderly":
            base_response = self._make_elderly_friendly(base_response)
        
        # Emotional adaptation
        if emotional_context.suggested_approach == "patient_supportive":
            base_response = f"Entendo que pode ser frustrante. {base_response} Vamos tentar juntos, sem pressa."
        elif emotional_context.suggested_approach == "enthusiastic_matching":
            base_response = f"Que ótimo! {base_response} Estou animado para ajudar!"
        elif emotional_context.suggested_approach == "gentle_brief":
            base_response = self._make_brief(base_response)
        
        # Accessibility adaptation
        if "visual_impairment" in self.user_profile.accessibility_needs:
            base_response = self._add_audio_descriptions(base_response)
        
        return base_response
    
    def _make_child_friendly(self, text: str) -> str:
        """Make response child-friendly."""
        # Simplify language and add encouragement
        text = text.replace("configurar", "ajustar")
        text = text.replace("executar", "fazer")
        return f"Oi! {text} Você está indo muito bem!"
    
    def _make_elderly_friendly(self, text: str) -> str:
        """Make response elderly-friendly."""
        # More formal, slower pace
        return f"Com prazer. {text} Posso repetir se necessário."
    
    def _make_brief(self, text: str) -> str:
        """Make response brief for tired users."""
        sentences = text.split('.')
        return sentences[0] + '.' if sentences else text
    
    def _add_audio_descriptions(self, text: str) -> str:
        """Add audio descriptions for visually impaired users."""
        return f"[Falando claramente] {text}"


class LearningEngine:
    """AI learning engine that improves with each interaction."""
    
    def __init__(self, db_path: Path, logger: logging.Logger):
        self.db_path = db_path
        self.logger = logger
        self._init_learning_db()
    
    def _init_learning_db(self):
        """Initialize learning database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS interaction_patterns (
                    id INTEGER PRIMARY KEY,
                    user_input TEXT,
                    context TEXT,
                    response TEXT,
                    user_satisfaction INTEGER,
                    timestamp TEXT,
                    emotional_state TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_preferences (
                    preference_key TEXT PRIMARY KEY,
                    preference_value TEXT,
                    confidence_score REAL,
                    last_updated TEXT
                )
            ''')
            conn.commit()
    
    async def learn_from_interaction(self, user_input: str, response: str, 
                                   satisfaction: int, emotional_context: EmotionalContext):
        """Learn from user interaction."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO interaction_patterns 
                    (user_input, response, user_satisfaction, timestamp, emotional_state)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    user_input, response, satisfaction, 
                    datetime.now().isoformat(), emotional_context.detected_emotion
                ))
                conn.commit()
            
            # Update preferences based on successful interactions
            if satisfaction >= 4:  # Good interaction
                await self._update_preferences(user_input, emotional_context)
        
        except Exception as e:
            self.logger.error(f"Learning error: {e}")
    
    async def _update_preferences(self, user_input: str, emotional_context: EmotionalContext):
        """Update user preferences based on successful interactions."""
        # Analyze patterns and update preferences
        # This is where machine learning would be implemented
        pass
    
    async def get_personalized_suggestions(self, current_context: str) -> List[str]:
        """Get personalized suggestions based on learning."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT user_input, COUNT(*) as frequency
                    FROM interaction_patterns 
                    WHERE user_satisfaction >= 4
                    GROUP BY user_input
                    ORDER BY frequency DESC
                    LIMIT 5
                ''')
                
                suggestions = []
                for row in cursor.fetchall():
                    suggestions.append(f"Que tal: {row[0]}")
                
                return suggestions
        
        except Exception as e:
            self.logger.error(f"Suggestion error: {e}")
            return ["Posso ajudar com tarefas, lembretes ou aprendizado."]


class PredictiveAssistance:
    """Predictive assistance that anticipates user needs."""
    
    def __init__(self, user_profile: UserProfile, logger: logging.Logger):
        self.user_profile = user_profile
        self.logger = logger
        self.daily_patterns = {}
    
    async def predict_next_need(self, current_time: datetime) -> Optional[str]:
        """Predict what the user might need next."""
        hour = current_time.hour
        
        # Time-based predictions
        if 7 <= hour <= 9:
            return "Bom dia! Quer que eu leia suas tarefas para hoje?"
        elif 12 <= hour <= 14:
            return "Hora do almoço! Lembrar de algum medicamento?"
        elif 18 <= hour <= 20:
            return "Como foi seu dia? Quer registrar algo importante?"
        elif 21 <= hour <= 23:
            return "Preparando para dormir? Posso tocar sons relaxantes."
        
        return None
    
    async def suggest_proactive_help(self, context: Dict[str, Any]) -> Optional[str]:
        """Suggest proactive help based on context."""
        
        # Health-based suggestions
        if self.user_profile.stress_level > 7:
            return "Percebo que você pode estar estressado. Que tal uma pausa para respirar?"
        
        # Learning-based suggestions
        if context.get("learning_streak", 0) > 3:
            return "Você está indo muito bem nos estudos! Quer um desafio maior?"
        
        # Productivity suggestions
        if context.get("tasks_completed", 0) > 5:
            return "Parabéns pela produtividade! Que tal uma pausa merecida?"
        
        return None


class AICompanion:
    """Revolutionary AI companion that truly understands and adapts."""
    
    def __init__(self, gem_assistant, logger: Optional[logging.Logger] = None):
        self.gem = gem_assistant
        self.logger = logger or logging.getLogger("AICompanion")
        
        # Initialize components
        self.user_profile = UserProfile()
        self.emotional_intelligence = EmotionalIntelligence(self.logger)
        self.adaptive_personality = AdaptivePersonality(self.user_profile, self.logger)
        
        # Initialize learning engine
        db_path = Path.home() / ".gem" / "data" / "ai_companion.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.learning_engine = LearningEngine(db_path, self.logger)
        
        self.predictive_assistance = PredictiveAssistance(self.user_profile, self.logger)
        
        # Companion state
        self.conversation_memory = []
        self.relationship_level = 1  # Grows with positive interactions
        self.trust_score = 0.5  # 0-1, affects response style
    
    async def initialize(self):
        """Initialize AI companion."""
        self.logger.info("Initializing AI Companion...")
        
        # Load user profile if exists
        await self._load_user_profile()
        
        # Start proactive assistance
        asyncio.create_task(self._proactive_assistance_loop())
        
        self.logger.info("AI Companion initialized - Ready to learn and adapt!")
    
    async def process_interaction(self, user_input: str, context: Dict[str, Any] = None) -> str:
        """Process user interaction with full AI companion capabilities."""
        
        # Analyze emotional state
        emotional_context = await self.emotional_intelligence.analyze_emotional_state(user_input)
        
        # Generate base response (from existing LLM)
        if self.gem.llm_handler:
            base_response = await self.gem.llm_handler.generate_response(
                user_input, self.gem.conversation_context
            )
        else:
            base_response = "Como posso ajudar você hoje?"
        
        # Adapt response with AI companion intelligence
        adapted_response = self.adaptive_personality.adapt_response_style(
            base_response, emotional_context
        )
        
        # Add predictive suggestions if appropriate
        suggestions = await self.learning_engine.get_personalized_suggestions(user_input)
        if suggestions and len(adapted_response) < 200:  # Don't overwhelm
            adapted_response += f"\n\nSugestão: {suggestions[0]}"
        
        # Update conversation memory
        self.conversation_memory.append({
            "input": user_input,
            "response": adapted_response,
            "emotion": emotional_context.detected_emotion,
            "timestamp": datetime.now().isoformat()
        })
        
        # Keep memory manageable
        if len(self.conversation_memory) > 50:
            self.conversation_memory = self.conversation_memory[-50:]
        
        return adapted_response
    
    async def learn_from_feedback(self, user_input: str, response: str, satisfaction: int):
        """Learn from user feedback."""
        emotional_context = await self.emotional_intelligence.analyze_emotional_state(user_input)
        await self.learning_engine.learn_from_interaction(
            user_input, response, satisfaction, emotional_context
        )
        
        # Update relationship metrics
        if satisfaction >= 4:
            self.relationship_level = min(10, self.relationship_level + 0.1)
            self.trust_score = min(1.0, self.trust_score + 0.05)
        elif satisfaction <= 2:
            self.trust_score = max(0.1, self.trust_score - 0.02)
    
    async def _proactive_assistance_loop(self):
        """Background loop for proactive assistance."""
        while True:
            try:
                current_time = datetime.now()
                
                # Check for predictive needs
                prediction = await self.predictive_assistance.predict_next_need(current_time)
                
                if prediction and self.trust_score > 0.7:  # Only if user trusts us
                    # Proactively offer help (would integrate with TTS)
                    self.logger.info(f"Proactive suggestion: {prediction}")
                    
                    if self.gem.tts_module:
                        await self.gem.tts_module.speak(prediction)
                
                # Wait before next check
                await asyncio.sleep(1800)  # Check every 30 minutes
            
            except Exception as e:
                self.logger.error(f"Proactive assistance error: {e}")
                await asyncio.sleep(3600)  # Wait longer on error
    
    async def _load_user_profile(self):
        """Load user profile from storage."""
        try:
            profile_path = Path.home() / ".gem" / "data" / "user_profile.json"
            if profile_path.exists():
                with open(profile_path, 'r') as f:
                    data = json.load(f)
                    # Update user profile with saved data
                    for key, value in data.items():
                        if hasattr(self.user_profile, key):
                            setattr(self.user_profile, key, value)
                
                self.logger.info("User profile loaded")
        
        except Exception as e:
            self.logger.error(f"Error loading user profile: {e}")
    
    async def save_user_profile(self):
        """Save user profile to storage."""
        try:
            profile_path = Path.home() / ".gem" / "data" / "user_profile.json"
            profile_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(profile_path, 'w') as f:
                json.dump(asdict(self.user_profile), f, indent=2)
            
            self.logger.info("User profile saved")
        
        except Exception as e:
            self.logger.error(f"Error saving user profile: {e}")
    
    async def get_companion_status(self) -> Dict[str, Any]:
        """Get AI companion status and metrics."""
        return {
            "relationship_level": self.relationship_level,
            "trust_score": self.trust_score,
            "interactions_today": len([
                m for m in self.conversation_memory 
                if datetime.fromisoformat(m["timestamp"]).date() == datetime.now().date()
            ]),
            "dominant_emotion": self._get_dominant_emotion(),
            "learning_active": True,
            "proactive_assistance": self.trust_score > 0.7
        }
    
    def _get_dominant_emotion(self) -> str:
        """Get user's dominant emotion from recent interactions."""
        if not self.conversation_memory:
            return "neutral"
        
        recent_emotions = [m["emotion"] for m in self.conversation_memory[-10:]]
        return max(set(recent_emotions), key=recent_emotions.count)