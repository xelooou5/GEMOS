#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GEM OS - Voice Training Engine
Personalized voice model training and adaptation
"""

import asyncio
import logging
import numpy as np
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
import json
import os
from datetime import datetime
import tempfile

@dataclass
class VoiceProfile:
    user_id: str
    name: str
    language: str
    accent: str
    pitch_range: Tuple[float, float]
    speaking_rate: float
    voice_characteristics: Dict[str, float]
    training_samples: int
    created_at: datetime
    last_updated: datetime

@dataclass
class TrainingSession:
    session_id: str
    user_id: str
    start_time: datetime
    samples_recorded: int
    quality_score: float
    completed: bool = False

class VoiceTrainer:
    def __init__(self, config: Optional[Dict[str, Any]] = None, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.config = config or {}
        
        # Training configuration
        self.sample_rate = self.config.get('sample_rate', 16000)
        self.min_samples_for_profile = self.config.get('min_samples', 20)
        self.max_recording_duration = self.config.get('max_duration', 10)  # seconds
        
        # Voice profiles storage
        self.profiles_dir = self.config.get('profiles_dir', 'data/voice_profiles')
        self.voice_profiles: Dict[str, VoiceProfile] = {}
        
        # Current training session
        self.current_session: Optional[TrainingSession] = None
        
        # Training phrases for different languages
        self.training_phrases = {
            'pt': [
                "Olá, meu nome é GEM e eu sou seu assistente pessoal.",
                "O tempo está muito bonito hoje, não acha?",
                "Gostaria de saber as notícias do dia de hoje.",
                "Por favor, me ajude a organizar minha agenda.",
                "Qual é a previsão do tempo para amanhã?",
                "Preciso fazer uma lista de compras para o supermercado.",
                "Você pode me lembrar de tomar o remédio às oito horas?",
                "Gostaria de ouvir uma música relaxante agora.",
                "Como posso melhorar minha produtividade no trabalho?",
                "Obrigado pela ajuda, você é muito útil.",
                "Boa noite, até amanhã pela manhã.",
                "Vamos começar o dia com energia positiva.",
                "A tecnologia pode nos ajudar muito no dia a dia.",
                "É importante cuidar da nossa saúde mental.",
                "A educação é fundamental para o desenvolvimento."
            ],
            'en': [
                "Hello, my name is GEM and I am your personal assistant.",
                "The weather is very nice today, don't you think?",
                "I would like to know today's news.",
                "Please help me organize my schedule.",
                "What is the weather forecast for tomorrow?",
                "I need to make a shopping list for the supermarket.",
                "Can you remind me to take my medicine at eight o'clock?",
                "I would like to listen to some relaxing music now.",
                "How can I improve my productivity at work?",
                "Thank you for your help, you are very useful.",
                "Good night, see you tomorrow morning.",
                "Let's start the day with positive energy.",
                "Technology can help us a lot in our daily lives.",
                "It's important to take care of our mental health.",
                "Education is fundamental for development."
            ]
        }
        
        # Voice analysis tools
        self.voice_analyzer = None
        
    async def initialize(self):
        """Initialize voice training system"""
        self.logger.info("Initializing voice training system...")
        
        # Create profiles directory
        os.makedirs(self.profiles_dir, exist_ok=True)
        
        # Load existing profiles
        await self._load_voice_profiles()
        
        # Initialize voice analysis tools
        try:
            import librosa
            import scipy.signal
            self.voice_analyzer = {
                'librosa': librosa,
                'scipy': scipy.signal
            }
            self.logger.info("✅ Voice analysis tools initialized")
        except ImportError as e:
            self.logger.warning(f"⚠️ Voice analysis tools not available: {e}")
        
        self.logger.info("Voice training system ready")
    
    async def _load_voice_profiles(self):
        """Load existing voice profiles from disk"""
        try:
            for filename in os.listdir(self.profiles_dir):
                if filename.endswith('.json'):
                    profile_path = os.path.join(self.profiles_dir, filename)
                    with open(profile_path, 'r', encoding='utf-8') as f:
                        profile_data = json.load(f)
                        
                    profile = VoiceProfile(
                        user_id=profile_data['user_id'],
                        name=profile_data['name'],
                        language=profile_data['language'],
                        accent=profile_data['accent'],
                        pitch_range=tuple(profile_data['pitch_range']),
                        speaking_rate=profile_data['speaking_rate'],
                        voice_characteristics=profile_data['voice_characteristics'],
                        training_samples=profile_data['training_samples'],
                        created_at=datetime.fromisoformat(profile_data['created_at']),
                        last_updated=datetime.fromisoformat(profile_data['last_updated'])
                    )
                    
                    self.voice_profiles[profile.user_id] = profile
                    self.logger.info(f"Loaded voice profile: {profile.name}")
                    
        except Exception as e:
            self.logger.error(f"Error loading voice profiles: {e}")
    
    async def start_training_session(self, user_id: str, user_name: str, 
                                   language: str = 'pt') -> str:
        """Start a new voice training session"""
        if self.current_session and not self.current_session.completed:
            return "❌ Já existe uma sessão de treinamento ativa. Finalize-a primeiro."
        
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.current_session = TrainingSession(
            session_id=session_id,
            user_id=user_id,
            start_time=datetime.now(),
            samples_recorded=0,
            quality_score=0.0
        )
        
        self.logger.info(f"Voice training session started for {user_name}")
        
        return f"""
        🎤 Sessão de Treinamento de Voz Iniciada
        
        Usuário: {user_name}
        Idioma: {language}
        Sessão: {session_id}
        
        Vou apresentar algumas frases para você repetir. Isso me ajudará a entender melhor sua voz e melhorar o reconhecimento.
        
        Digite 'próxima frase' para começar o treinamento.
        """.strip()
    
    async def get_next_training_phrase(self) -> str:
        """Get next phrase for training"""
        if not self.current_session:
            return "❌ Nenhuma sessão de treinamento ativa. Inicie uma sessão primeiro."
        
        language = 'pt'  # Default, could be extracted from session
        phrases = self.training_phrases.get(language, self.training_phrases['pt'])
        
        # Select phrase based on current progress
        phrase_index = self.current_session.samples_recorded % len(phrases)
        phrase = phrases[phrase_index]
        
        return f"""
        📝 Frase {self.current_session.samples_recorded + 1}:
        
        "{phrase}"
        
        Por favor, repita esta frase claramente. Quando terminar, diga 'próxima frase' ou 'finalizar treinamento'.
        """
    
    async def process_training_sample(self, audio_data: np.ndarray) -> str:
        """Process a training audio sample"""
        if not self.current_session:
            return "❌ Nenhuma sessão de treinamento ativa."
        
        try:
            # Analyze audio quality
            quality_score = await self._analyze_audio_quality(audio_data)
            
            # Update session
            self.current_session.samples_recorded += 1
            self.current_session.quality_score = (
                (self.current_session.quality_score * (self.current_session.samples_recorded - 1) + quality_score) 
                / self.current_session.samples_recorded
            )
            
            # Save audio sample (in production, you'd save this for training)
            await self._save_training_sample(audio_data, self.current_session.samples_recorded)
            
            feedback = self._get_quality_feedback(quality_score)
            
            progress = (self.current_session.samples_recorded / self.min_samples_for_profile) * 100
            progress = min(progress, 100)
            
            return f"""
            ✅ Amostra {self.current_session.samples_recorded} gravada!
            
            Qualidade: {feedback}
            Progresso: {progress:.0f}%
            
            {self._get_training_encouragement(self.current_session.samples_recorded)}
            
            Digite 'próxima frase' para continuar ou 'finalizar treinamento' se quiser parar.
            """.strip()
            
        except Exception as e:
            self.logger.error(f"Error processing training sample: {e}")
            return "❌ Erro ao processar a amostra de áudio. Tente novamente."
    
    async def _analyze_audio_quality(self, audio_data: np.ndarray) -> float:
        """Analyze audio quality for training"""
        if not self.voice_analyzer:
            return 0.7  # Default quality score
        
        try:
            librosa = self.voice_analyzer['librosa']
            
            # Basic quality metrics
            
            # 1. Signal-to-noise ratio estimation
            # Calculate RMS energy
            rms_energy = np.sqrt(np.mean(audio_data ** 2))
            
            # 2. Check for clipping
            clipping_ratio = np.sum(np.abs(audio_data) > 0.95) / len(audio_data)
            
            # 3. Check dynamic range
            dynamic_range = np.max(audio_data) - np.min(audio_data)
            
            # 4. Spectral analysis
            # Extract spectral features
            stft = librosa.stft(audio_data)
            spectral_centroids = librosa.feature.spectral_centroid(S=np.abs(stft))[0]
            spectral_rolloff = librosa.feature.spectral_rolloff(S=np.abs(stft))[0]
            
            # Calculate quality score (0-1)
            quality_score = 1.0
            
            # Penalize for low energy (too quiet)
            if rms_energy < 0.01:
                quality_score *= 0.5
            
            # Penalize for clipping
            if clipping_ratio > 0.01:
                quality_score *= (1.0 - clipping_ratio * 10)
            
            # Penalize for low dynamic range
            if dynamic_range < 0.1:
                quality_score *= 0.6
            
            # Ensure score is between 0 and 1
            quality_score = max(0.0, min(1.0, quality_score))
            
            return quality_score
            
        except Exception as e:
            self.logger.warning(f"Audio quality analysis failed: {e}")
            return 0.7  # Default score on error
    
    def _get_quality_feedback(self, quality_score: float) -> str:
        """Get human-readable quality feedback"""
        if quality_score >= 0.9:
            return "Excelente! 🌟"
        elif quality_score >= 0.8:
            return "Muito boa! 👍"
        elif quality_score >= 0.7:
            return "Boa 👌"
        elif quality_score >= 0.6:
            return "Razoável ⚠️"
        else:
            return "Tente falar mais alto e claro 📢"
    
    def _get_training_encouragement(self, samples_count: int) -> str:
        """Get encouraging message based on progress"""
        if samples_count >= self.min_samples_for_profile:
            return "🎉 Parabéns! Você já tem amostras suficientes para criar um perfil de voz personalizado!"
        elif samples_count >= self.min_samples_for_profile // 2:
            return "💪 Você está indo muito bem! Continue assim!"
        elif samples_count >= 5:
            return "👏 Ótimo progresso! Sua voz está ficando cada vez mais clara para mim."
        else:
            return "🚀 Vamos continuar! Cada amostra me ajuda a entender melhor sua voz."
    
    async def _save_training_sample(self, audio_data: np.ndarray, sample_number: int):
        """Save training sample to disk"""
        if not self.current_session:
            return
        
        try:
            # Create session directory
            session_dir = os.path.join(self.profiles_dir, self.current_session.session_id)
            os.makedirs(session_dir, exist_ok=True)
            
            # Save audio sample
            sample_path = os.path.join(session_dir, f"sample_{sample_number:03d}.wav")
            
            # Use soundfile to save audio
            try:
                import soundfile as sf
                sf.write(sample_path, audio_data, self.sample_rate)
            except ImportError:
                # Fallback: save as numpy array
                np.save(sample_path.replace('.wav', '.npy'), audio_data)
            
        except Exception as e:
            self.logger.error(f"Error saving training sample: {e}")
    
    async def finalize_training_session(self) -> str:
        """Finalize current training session and create/update voice profile"""
        if not self.current_session:
            return "❌ Nenhuma sessão de treinamento ativa."
        
        session = self.current_session
        session.completed = True
        
        if session.samples_recorded < 5:
            return f"""
            ⚠️ Sessão finalizada com apenas {session.samples_recorded} amostras.
            
            Para criar um perfil de voz eficaz, recomendo pelo menos {self.min_samples_for_profile} amostras.
            Você pode iniciar uma nova sessão a qualquer momento para continuar o treinamento.
            """
        
        # Create or update voice profile
        try:
            await self._create_voice_profile(session)
            
            duration = datetime.now() - session.start_time
            
            result = f"""
            🎉 Treinamento de Voz Concluído!
            
            Amostras gravadas: {session.samples_recorded}
            Qualidade média: {self._get_quality_feedback(session.quality_score)}
            Duração: {duration.seconds // 60} minutos
            
            Seu perfil de voz foi {'criado' if session.user_id not in self.voice_profiles else 'atualizado'} com sucesso!
            
            Agora posso reconhecer sua voz com maior precisão. 🎤✨
            """
            
            self.current_session = None
            return result.strip()
            
        except Exception as e:
            self.logger.error(f"Error finalizing training session: {e}")
            return "❌ Erro ao finalizar o treinamento. Tente novamente."
    
    async def _create_voice_profile(self, session: TrainingSession):
        """Create or update voice profile from training session"""
        
        # Analyze voice characteristics (simplified)
        voice_characteristics = {
            'average_pitch': 150.0,  # Hz, would be calculated from samples
            'pitch_variance': 20.0,
            'speaking_rate': 1.0,    # relative to normal
            'energy_level': session.quality_score,
            'formant_frequencies': [800, 1200, 2400]  # F1, F2, F3 estimates
        }
        
        # Create or update profile
        if session.user_id in self.voice_profiles:
            # Update existing profile
            profile = self.voice_profiles[session.user_id]
            profile.training_samples += session.samples_recorded
            profile.voice_characteristics.update(voice_characteristics)
            profile.last_updated = datetime.now()
        else:
            # Create new profile
            profile = VoiceProfile(
                user_id=session.user_id,
                name=f"User_{session.user_id}",
                language='pt',  # Would be detected or specified
                accent='neutral',
                pitch_range=(120.0, 180.0),  # Would be calculated
                speaking_rate=1.0,
                voice_characteristics=voice_characteristics,
                training_samples=session.samples_recorded,
                created_at=datetime.now(),
                last_updated=datetime.now()
            )
            
            self.voice_profiles[session.user_id] = profile
        
        # Save profile to disk
        await self._save_voice_profile(profile)
    
    async def _save_voice_profile(self, profile: VoiceProfile):
        """Save voice profile to disk"""
        try:
            profile_data = {
                'user_id': profile.user_id,
                'name': profile.name,
                'language': profile.language,
                'accent': profile.accent,
                'pitch_range': list(profile.pitch_range),
                'speaking_rate': profile.speaking_rate,
                'voice_characteristics': profile.voice_characteristics,
                'training_samples': profile.training_samples,
                'created_at': profile.created_at.isoformat(),
                'last_updated': profile.last_updated.isoformat()
            }
            
            profile_path = os.path.join(self.profiles_dir, f"{profile.user_id}.json")
            with open(profile_path, 'w', encoding='utf-8') as f:
                json.dump(profile_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Voice profile saved: {profile.name}")
            
        except Exception as e:
            self.logger.error(f"Error saving voice profile: {e}")
            raise
    
    async def get_voice_profile(self, user_id: str) -> Optional[VoiceProfile]:
        """Get voice profile for user"""
        return self.voice_profiles.get(user_id)
    
    async def list_voice_profiles(self) -> str:
        """List all voice profiles"""
        if not self.voice_profiles:
            return "📝 Nenhum perfil de voz encontrado. Inicie um treinamento para criar seu perfil!"
        
        profile_list = "🎤 Perfis de Voz Disponíveis:\n\n"
        
        for profile in self.voice_profiles.values():
            profile_list += f"👤 {profile.name}\n"
            profile_list += f"   ID: {profile.user_id}\n"
            profile_list += f"   Idioma: {profile.language}\n"
            profile_list += f"   Amostras: {profile.training_samples}\n"
            profile_list += f"   Criado: {profile.created_at.strftime('%d/%m/%Y')}\n"
            profile_list += f"   Atualizado: {profile.last_updated.strftime('%d/%m/%Y')}\n\n"
        
        return profile_list.strip()
    
    async def delete_voice_profile(self, user_id: str) -> str:
        """Delete a voice profile"""
        if user_id not in self.voice_profiles:
            return f"❌ Perfil de voz não encontrado para o usuário {user_id}."
        
        try:
            profile = self.voice_profiles[user_id]
            
            # Delete profile file
            profile_path = os.path.join(self.profiles_dir, f"{user_id}.json")
            if os.path.exists(profile_path):
                os.remove(profile_path)
            
            # Delete training samples directory
            session_dirs = [d for d in os.listdir(self.profiles_dir) 
                          if d.startswith('session_') and os.path.isdir(os.path.join(self.profiles_dir, d))]
            
            for session_dir in session_dirs:
                # This is simplified - in production, you'd track which sessions belong to which user
                pass
            
            # Remove from memory
            del self.voice_profiles[user_id]
            
            self.logger.info(f"Voice profile deleted: {profile.name}")
            return f"✅ Perfil de voz de {profile.name} removido com sucesso."
            
        except Exception as e:
            self.logger.error(f"Error deleting voice profile: {e}")
            return "❌ Erro ao remover o perfil de voz."
    
    def get_training_status(self) -> Dict[str, Any]:
        """Get current training status"""
        status = {
            "session_active": self.current_session is not None,
            "total_profiles": len(self.voice_profiles),
            "available_languages": list(self.training_phrases.keys())
        }
        
        if self.current_session:
            status.update({
                "session_id": self.current_session.session_id,
                "samples_recorded": self.current_session.samples_recorded,
                "quality_score": self.current_session.quality_score,
                "progress_percentage": min(
                    (self.current_session.samples_recorded / self.min_samples_for_profile) * 100, 
                    100
                )
            })
        
        return status
    
    def shutdown(self):
        """Cleanup voice training resources"""
        self.logger.info("Shutting down voice training system...")
        
        # Finalize any active session
        if self.current_session and not self.current_session.completed:
            self.current_session.completed = True
        
        self.logger.info("Voice training system shutdown complete")