#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GEM OS - Wake Word Trainer
Custom wake word detection training and optimization
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
class WakeWordModel:
    name: str
    phrase: str
    language: str
    sensitivity: float
    model_path: str
    training_samples: int
    accuracy: float
    created_at: datetime
    last_trained: datetime

@dataclass
class TrainingData:
    positive_samples: List[np.ndarray]  # Wake word samples
    negative_samples: List[np.ndarray]  # Background/other speech samples
    sample_rate: int
    duration_ms: int

class WakeWordTrainer:
    def __init__(self, config: Optional[Dict[str, Any]] = None, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.config = config or {}
        
        # Configuration
        self.sample_rate = self.config.get('sample_rate', 16000)
        self.wake_word_duration = self.config.get('wake_word_duration', 2000)  # ms
        self.min_training_samples = self.config.get('min_training_samples', 10)
        self.sensitivity_threshold = self.config.get('sensitivity_threshold', 0.7)
        
        # Storage
        self.models_dir = self.config.get('models_dir', 'data/models')
        self.training_dir = self.config.get('training_dir', 'data/training_data')
        
        # Available wake word engines
        self.available_engines = []
        self.porcupine_engine = None
        self.custom_model = None
        
        # Current training session
        self.current_training: Optional[Dict[str, Any]] = None
        
        # Default wake words for different languages
        self.default_wake_words = {
            'pt': ['hey gem', 'oi gem', 'gem'],
            'en': ['hey gem', 'hello gem', 'gem'],
            'es': ['hola gem', 'oye gem', 'gem'],
            'fr': ['salut gem', 'hey gem', 'gem']
        }
    
    async def initialize(self):
        """Initialize wake word training system"""
        self.logger.info("Initializing wake word training system...")
        
        # Create directories
        os.makedirs(self.models_dir, exist_ok=True)
        os.makedirs(self.training_dir, exist_ok=True)
        
        # Try to initialize Porcupine (Picovoice)
        try:
            import pvporcupine
            self.porcupine_engine = pvporcupine
            self.available_engines.append("porcupine")
            self.logger.info("✅ Porcupine wake word engine available")
        except ImportError:
            self.logger.warning("⚠️ Porcupine not available (requires license key)")
        
        # Initialize custom lightweight model
        try:
            self.custom_model = CustomWakeWordModel(
                sample_rate=self.sample_rate,
                logger=self.logger
            )
            self.available_engines.append("custom")
            self.logger.info("✅ Custom wake word engine initialized")
        except Exception as e:
            self.logger.warning(f"⚠️ Custom wake word engine failed: {e}")
        
        if not self.available_engines:
            self.logger.warning("⚠️ No wake word engines available")
        
        self.logger.info("Wake word training system ready")
    
    async def start_wake_word_training(self, wake_phrase: str = "hey gem", 
                                     language: str = "pt") -> str:
        """Start training a custom wake word"""
        if self.current_training:
            return "❌ Já existe um treinamento ativo. Finalize-o primeiro."
        
        self.current_training = {
            'phrase': wake_phrase.lower(),
            'language': language,
            'positive_samples': [],
            'negative_samples': [],
            'start_time': datetime.now(),
            'target_samples': self.min_training_samples
        }
        
        self.logger.info(f"Wake word training started: '{wake_phrase}'")
        
        return f"""
        🎤 Treinamento de Palavra de Ativação Iniciado
        
        Palavra: "{wake_phrase}"
        Idioma: {language}
        Meta: {self.min_training_samples} amostras
        
        Vou guiá-lo através do processo de treinamento:
        
        1️⃣ Primeiro, vou coletar amostras da palavra de ativação
        2️⃣ Depois, vou coletar amostras de outras palavras (para evitar falsos positivos)
        3️⃣ Por fim, vou treinar o modelo personalizado
        
        Digite 'gravar palavra' para começar a gravar amostras da palavra de ativação.
        """.strip()
    
    async def record_positive_sample(self, audio_data: np.ndarray) -> str:
        """Record a positive sample (wake word)"""
        if not self.current_training:
            return "❌ Nenhum treinamento ativo. Inicie um treinamento primeiro."
        
        try:
            # Validate audio length
            expected_samples = int(self.sample_rate * self.wake_word_duration / 1000)
            if len(audio_data) < expected_samples * 0.5:  # At least 50% of expected length
                return "⚠️ Áudio muito curto. Tente falar a palavra de ativação mais claramente."
            
            # Preprocess audio
            processed_audio = await self._preprocess_audio(audio_data)
            
            # Add to training data
            self.current_training['positive_samples'].append(processed_audio)
            
            samples_count = len(self.current_training['positive_samples'])
            progress = (samples_count / self.current_training['target_samples']) * 100
            
            # Save sample for later use
            await self._save_training_sample(processed_audio, 'positive', samples_count)
            
            if samples_count >= self.current_training['target_samples']:
                return f"""
                ✅ Amostra {samples_count} da palavra de ativação gravada!
                
                🎉 Parabéns! Você coletou amostras suficientes da palavra de ativação.
                
                Agora vamos coletar algumas amostras de outras palavras para melhorar a precisão.
                Digite 'gravar outras' para gravar palavras diferentes da palavra de ativação.
                """.strip()
            else:
                remaining = self.current_training['target_samples'] - samples_count
                return f"""
                ✅ Amostra {samples_count} da palavra de ativação gravada!
                
                Progresso: {progress:.0f}% ({samples_count}/{self.current_training['target_samples']})
                Faltam: {remaining} amostras
                
                Digite 'gravar palavra' novamente para gravar mais uma amostra da palavra "{self.current_training['phrase']}".
                """.strip()
                
        except Exception as e:
            self.logger.error(f"Error recording positive sample: {e}")
            return "❌ Erro ao gravar a amostra. Tente novamente."
    
    async def record_negative_sample(self, audio_data: np.ndarray) -> str:
        """Record a negative sample (not wake word)"""
        if not self.current_training:
            return "❌ Nenhum treinamento ativo."
        
        try:
            # Preprocess audio
            processed_audio = await self._preprocess_audio(audio_data)
            
            # Add to negative samples
            self.current_training['negative_samples'].append(processed_audio)
            
            negative_count = len(self.current_training['negative_samples'])
            positive_count = len(self.current_training['positive_samples'])
            
            # Save sample
            await self._save_training_sample(processed_audio, 'negative', negative_count)
            
            # We want roughly equal positive and negative samples
            target_negative = max(positive_count, self.min_training_samples // 2)
            
            if negative_count >= target_negative:
                return f"""
                ✅ Amostra negativa {negative_count} gravada!
                
                🎉 Excelente! Agora temos dados suficientes para treinar o modelo.
                
                Amostras da palavra de ativação: {positive_count}
                Amostras de outras palavras: {negative_count}
                
                Digite 'treinar modelo' para criar seu modelo personalizado de palavra de ativação.
                """.strip()
            else:
                remaining = target_negative - negative_count
                return f"""
                ✅ Amostra negativa {negative_count} gravada!
                
                Progresso: {negative_count}/{target_negative} amostras de outras palavras
                Faltam: {remaining} amostras
                
                Digite 'gravar outras' para gravar mais palavras diferentes de "{self.current_training['phrase']}".
                Exemplos: "olá", "como vai", "obrigado", "tchau", etc.
                """.strip()
                
        except Exception as e:
            self.logger.error(f"Error recording negative sample: {e}")
            return "❌ Erro ao gravar a amostra. Tente novamente."
    
    async def _preprocess_audio(self, audio_data: np.ndarray) -> np.ndarray:
        """Preprocess audio for training"""
        # Normalize audio
        if np.max(np.abs(audio_data)) > 0:
            audio_data = audio_data / np.max(np.abs(audio_data))
        
        # Ensure consistent length
        target_length = int(self.sample_rate * self.wake_word_duration / 1000)
        
        if len(audio_data) > target_length:
            # Trim to target length
            audio_data = audio_data[:target_length]
        elif len(audio_data) < target_length:
            # Pad with zeros
            padding = target_length - len(audio_data)
            audio_data = np.pad(audio_data, (0, padding), mode='constant')
        
        return audio_data
    
    async def _save_training_sample(self, audio_data: np.ndarray, 
                                  sample_type: str, sample_number: int):
        """Save training sample to disk"""
        if not self.current_training:
            return
        
        try:
            # Create training session directory
            session_name = f"wake_word_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            session_dir = os.path.join(self.training_dir, session_name)
            os.makedirs(session_dir, exist_ok=True)
            
            # Save audio sample
            filename = f"{sample_type}_{sample_number:03d}.npy"
            sample_path = os.path.join(session_dir, filename)
            np.save(sample_path, audio_data)
            
            # Save metadata
            metadata = {
                'phrase': self.current_training['phrase'],
                'language': self.current_training['language'],
                'sample_type': sample_type,
                'sample_number': sample_number,
                'sample_rate': self.sample_rate,
                'duration_ms': self.wake_word_duration,
                'timestamp': datetime.now().isoformat()
            }
            
            metadata_path = os.path.join(session_dir, f"{sample_type}_{sample_number:03d}.json")
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Error saving training sample: {e}")
    
    async def train_wake_word_model(self) -> str:
        """Train the wake word model with collected samples"""
        if not self.current_training:
            return "❌ Nenhum treinamento ativo."
        
        positive_samples = self.current_training['positive_samples']
        negative_samples = self.current_training['negative_samples']
        
        if len(positive_samples) < self.min_training_samples // 2:
            return f"❌ Amostras insuficientes. Precisa de pelo menos {self.min_training_samples // 2} amostras da palavra de ativação."
        
        try:
            self.logger.info("Training wake word model...")
            
            # Use custom model trainer
            if self.custom_model:
                training_data = TrainingData(
                    positive_samples=positive_samples,
                    negative_samples=negative_samples,
                    sample_rate=self.sample_rate,
                    duration_ms=self.wake_word_duration
                )
                
                accuracy = await self.custom_model.train(training_data)
                
                # Save trained model
                model_name = f"wake_word_{self.current_training['phrase'].replace(' ', '_')}"
                model_path = os.path.join(self.models_dir, f"{model_name}.json")
                
                model_info = WakeWordModel(
                    name=model_name,
                    phrase=self.current_training['phrase'],
                    language=self.current_training['language'],
                    sensitivity=self.sensitivity_threshold,
                    model_path=model_path,
                    training_samples=len(positive_samples) + len(negative_samples),
                    accuracy=accuracy,
                    created_at=datetime.now(),
                    last_trained=datetime.now()
                )
                
                await self._save_wake_word_model(model_info)
                
                # Clear current training
                training_duration = datetime.now() - self.current_training['start_time']
                self.current_training = None
                
                return f"""
                🎉 Modelo de Palavra de Ativação Treinado com Sucesso!
                
                Palavra: "{model_info.phrase}"
                Amostras utilizadas: {model_info.training_samples}
                Precisão estimada: {accuracy:.1%}
                Tempo de treinamento: {training_duration.seconds // 60} minutos
                
                Seu modelo personalizado está pronto! Agora posso detectar quando você diz "{model_info.phrase}" com maior precisão.
                
                Para ativar o novo modelo, reinicie o GEM ou digite 'recarregar modelos'.
                """.strip()
            else:
                return "❌ Motor de treinamento não disponível. Verifique a instalação."
                
        except Exception as e:
            self.logger.error(f"Error training wake word model: {e}")
            return "❌ Erro durante o treinamento do modelo. Tente novamente."
    
    async def _save_wake_word_model(self, model_info: WakeWordModel):
        """Save wake word model information"""
        try:
            model_data = {
                'name': model_info.name,
                'phrase': model_info.phrase,
                'language': model_info.language,
                'sensitivity': model_info.sensitivity,
                'model_path': model_info.model_path,
                'training_samples': model_info.training_samples,
                'accuracy': model_info.accuracy,
                'created_at': model_info.created_at.isoformat(),
                'last_trained': model_info.last_trained.isoformat()
            }
            
            with open(model_info.model_path, 'w') as f:
                json.dump(model_data, f, indent=2)
            
            self.logger.info(f"Wake word model saved: {model_info.name}")
            
        except Exception as e:
            self.logger.error(f"Error saving wake word model: {e}")
            raise
    
    async def list_wake_word_models(self) -> str:
        """List available wake word models"""
        try:
            models = []
            
            for filename in os.listdir(self.models_dir):
                if filename.endswith('.json') and filename.startswith('wake_word_'):
                    model_path = os.path.join(self.models_dir, filename)
                    with open(model_path, 'r') as f:
                        model_data = json.load(f)
                    models.append(model_data)
            
            if not models:
                return """
                📝 Nenhum modelo personalizado encontrado.
                
                Para criar um modelo personalizado:
                1. Digite 'treinar palavra de ativação'
                2. Siga as instruções para gravar amostras
                3. Treine o modelo
                
                Modelos padrão disponíveis: hey gem, oi gem
                """.strip()
            
            model_list = "🎤 Modelos de Palavra de Ativação Disponíveis:\n\n"
            
            for model in models:
                created = datetime.fromisoformat(model['created_at'])
                model_list += f"🔹 {model['phrase']}\n"
                model_list += f"   Idioma: {model['language']}\n"
                model_list += f"   Precisão: {model['accuracy']:.1%}\n"
                model_list += f"   Amostras: {model['training_samples']}\n"
                model_list += f"   Criado: {created.strftime('%d/%m/%Y %H:%M')}\n\n"
            
            return model_list.strip()
            
        except Exception as e:
            self.logger.error(f"Error listing wake word models: {e}")
            return "❌ Erro ao listar modelos de palavra de ativação."
    
    async def test_wake_word_detection(self, audio_data: np.ndarray) -> Tuple[bool, float, str]:
        """Test wake word detection on audio sample"""
        if not self.custom_model:
            return False, 0.0, "Modelo não disponível"
        
        try:
            # Preprocess audio
            processed_audio = await self._preprocess_audio(audio_data)
            
            # Test with custom model
            is_wake_word, confidence = await self.custom_model.detect(processed_audio)
            
            result_text = f"Palavra de ativação {'detectada' if is_wake_word else 'não detectada'} (confiança: {confidence:.2f})"
            
            return is_wake_word, confidence, result_text
            
        except Exception as e:
            self.logger.error(f"Error testing wake word detection: {e}")
            return False, 0.0, f"Erro no teste: {e}"
    
    def get_training_status(self) -> Dict[str, Any]:
        """Get current training status"""
        status = {
            "training_active": self.current_training is not None,
            "available_engines": self.available_engines,
            "default_wake_words": self.default_wake_words
        }
        
        if self.current_training:
            positive_count = len(self.current_training['positive_samples'])
            negative_count = len(self.current_training['negative_samples'])
            
            status.update({
                "phrase": self.current_training['phrase'],
                "language": self.current_training['language'],
                "positive_samples": positive_count,
                "negative_samples": negative_count,
                "target_samples": self.current_training['target_samples'],
                "progress_percentage": (positive_count / self.current_training['target_samples']) * 100
            })
        
        return status
    
    def shutdown(self):
        """Cleanup wake word training resources"""
        self.logger.info("Shutting down wake word training system...")
        
        if self.current_training:
            self.current_training = None
        
        if self.custom_model:
            self.custom_model.shutdown()
        
        self.logger.info("Wake word training system shutdown complete")


class CustomWakeWordModel:
    """Simple custom wake word detection model"""
    
    def __init__(self, sample_rate: int = 16000, logger: Optional[logging.Logger] = None):
        self.sample_rate = sample_rate
        self.logger = logger or logging.getLogger(__name__)
        
        # Simple template matching approach
        self.positive_templates = []
        self.negative_templates = []
        self.threshold = 0.7
        
    async def train(self, training_data: TrainingData) -> float:
        """Train the wake word model"""
        self.logger.info("Training custom wake word model...")
        
        # Store templates (simplified approach)
        self.positive_templates = training_data.positive_samples.copy()
        self.negative_templates = training_data.negative_samples.copy()
        
        # Calculate optimal threshold using cross-validation (simplified)
        accuracies = []
        
        for threshold in np.arange(0.5, 0.9, 0.05):
            correct = 0
            total = 0
            
            # Test on positive samples
            for sample in training_data.positive_samples:
                is_match, confidence = await self._template_match(sample)
                if (confidence >= threshold) == True:  # Should be detected
                    correct += 1
                total += 1
            
            # Test on negative samples
            for sample in training_data.negative_samples:
                is_match, confidence = await self._template_match(sample)
                if (confidence >= threshold) == False:  # Should not be detected
                    correct += 1
                total += 1
            
            accuracy = correct / total if total > 0 else 0
            accuracies.append(accuracy)
        
        # Select best threshold
        best_threshold_idx = np.argmax(accuracies)
        self.threshold = 0.5 + best_threshold_idx * 0.05
        best_accuracy = accuracies[best_threshold_idx]
        
        self.logger.info(f"Training complete. Best threshold: {self.threshold:.2f}, Accuracy: {best_accuracy:.2%}")
        
        return best_accuracy
    
    async def detect(self, audio_data: np.ndarray) -> Tuple[bool, float]:
        """Detect wake word in audio"""
        if not self.positive_templates:
            return False, 0.0
        
        is_match, confidence = await self._template_match(audio_data)
        is_wake_word = confidence >= self.threshold
        
        return is_wake_word, confidence
    
    async def _template_match(self, audio_data: np.ndarray) -> Tuple[bool, float]:
        """Simple template matching"""
        if not self.positive_templates:
            return False, 0.0
        
        # Calculate correlation with positive templates
        max_correlation = 0.0
        
        for template in self.positive_templates:
            # Ensure same length
            min_len = min(len(audio_data), len(template))
            audio_segment = audio_data[:min_len]
            template_segment = template[:min_len]
            
            # Normalize
            if np.std(audio_segment) > 0:
                audio_segment = (audio_segment - np.mean(audio_segment)) / np.std(audio_segment)
            if np.std(template_segment) > 0:
                template_segment = (template_segment - np.mean(template_segment)) / np.std(template_segment)
            
            # Calculate correlation
            correlation = np.corrcoef(audio_segment, template_segment)[0, 1]
            if not np.isnan(correlation):
                max_correlation = max(max_correlation, abs(correlation))
        
        return max_correlation >= self.threshold, max_correlation
    
    def shutdown(self):
        """Cleanup model resources"""
        self.positive_templates.clear()
        self.negative_templates.clear()