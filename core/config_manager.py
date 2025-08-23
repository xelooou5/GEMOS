#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
💎 GEM OS - Configuration Manager
Flexible configuration management for accessibility and customization
"""

import json
import os
import yaml
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Any, Optional, Union
import logging


@dataclass
class AudioConfig:
    """Audio system configuration."""
    sample_rate: int = 16000
    channels: int = 1
    chunk_size: int = 1024
    device_index: Optional[int] = None
    input_device: Optional[str] = None
    output_device: Optional[str] = None
    noise_reduction: bool = True
    echo_cancellation: bool = True
    auto_gain_control: bool = True
    volume_threshold: float = 0.01
    silence_timeout: float = 2.0


@dataclass
class STTConfig:
    """Speech-to-Text configuration."""
    engine: str = "whisper"  # whisper, vosk, google
    model: str = "base"
    language: str = "en-US"
    secondary_language: str = "pt-BR"
    energy_threshold: int = 300
    dynamic_energy_threshold: bool = True
    pause_threshold: float = 0.8
    phrase_threshold: float = 0.3
    non_speaking_duration: float = 0.5


@dataclass
class TTSConfig:
    """Text-to-Speech configuration."""
    engine: str = "pyttsx3"  # pyttsx3, espeak, edge-tts, gtts
    voice: Optional[str] = None
    rate: int = 110  # Much slower for human-like, accessible speech
    volume: float = 0.75  # Gentle, comfortable volume
    language: str = "en-US"
    secondary_language: str = "pt-BR"
    gender: str = "female"  # Prioritize calm female voices
    age: str = "adult"  # child, adult, elderly
    voice_style: str = "calm"  # calm, energetic, professional
    pause_between_sentences: float = 0.8  # Natural pauses for accessibility


@dataclass
class LLMConfig:
    """Large Language Model configuration."""
    provider: str = "ollama"  # ollama, openai, local
    model: str = "phi3:mini"
    base_url: str = "http://localhost:11434"
    api_key: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 1000
    context_length: int = 4096
    system_prompt: str = "You are GEM, an accessible and friendly voice assistant. You can communicate in English and Portuguese (Brazil). Always prioritize accessibility and user comfort."
    secondary_prompt: str = "Você é o GEM, um assistente de voz acessível e amigável. Você pode se comunicar em inglês e português (Brasil). Sempre priorize acessibilidade e conforto do usuário."


@dataclass
class AccessibilityConfig:
    """Accessibility features configuration."""
    screen_reader_support: bool = True
    high_contrast_mode: bool = False
    large_text_mode: bool = False
    voice_commands_only: bool = False
    slow_speech_mode: bool = False
    repeat_confirmations: bool = True
    audio_descriptions: bool = True
    keyboard_navigation: bool = True


@dataclass
class HealthConfig:
    """Health and wellness configuration."""
    medication_reminders: bool = True
    exercise_reminders: bool = True
    hydration_reminders: bool = True
    posture_reminders: bool = True
    break_reminders: bool = True
    sleep_tracking: bool = False
    mood_tracking: bool = False


@dataclass
class GeneralConfig:
    """General system configuration."""
    profile_name: str = "default"
    language: str = "en-US"
    secondary_language: str = "pt-BR"
    timezone: str = "America/Sao_Paulo"
    wake_words: list = None
    response_delay: float = 0.5
    auto_save: bool = True
    privacy_mode: bool = True
    offline_mode: bool = True
    debug_mode: bool = False
    
    def __post_init__(self):
        if self.wake_words is None:
            self.wake_words = ["hey gem", "hi gem", "gem", "oi gem", "olá gem"]


@dataclass
class GEMConfig:
    """Main GEM OS configuration."""
    general: GeneralConfig
    audio: AudioConfig
    stt: STTConfig
    tts: TTSConfig
    llm: LLMConfig
    accessibility: AccessibilityConfig
    health: HealthConfig


class GEMConfigManager:
    """Configuration manager for GEM OS."""
    
    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir or Path.home() / ".gem" / "config"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = logging.getLogger("ConfigManager")
        self.config: Optional[GEMConfig] = None
        self.current_profile = "default"
    
    def get_config_path(self, profile: str = "default") -> Path:
        """Get configuration file path for a profile."""
        return self.config_dir / f"{profile}.yaml"
    
    def create_default_config(self) -> GEMConfig:
        """Create default configuration."""
        return GEMConfig(
            general=GeneralConfig(),
            audio=AudioConfig(),
            stt=STTConfig(),
            tts=TTSConfig(),
            llm=LLMConfig(),
            accessibility=AccessibilityConfig(),
            health=HealthConfig()
        )
    
    def load(self, profile: str = "default") -> GEMConfig:
        """Load configuration from file."""
        config_path = self.get_config_path(profile)
        
        if not config_path.exists():
            self.logger.info(f"Creating default configuration for profile '{profile}'")
            self.config = self.create_default_config()
            self.config.general.profile_name = profile
            self.save(profile)
        else:
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                
                self.config = self._dict_to_config(data)
                self.logger.info(f"Configuration loaded from {config_path}")
            
            except Exception as e:
                self.logger.error(f"Error loading configuration: {e}")
                self.logger.info("Using default configuration")
                self.config = self.create_default_config()
        
        self.current_profile = profile
        return self.config
    
    def save(self, profile: Optional[str] = None) -> bool:
        """Save configuration to file."""
        if not self.config:
            self.logger.error("No configuration to save")
            return False
        
        profile = profile or self.current_profile
        config_path = self.get_config_path(profile)
        
        try:
            data = self._config_to_dict(self.config)
            
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
            
            self.logger.info(f"Configuration saved to {config_path}")
            return True
        
        except Exception as e:
            self.logger.error(f"Error saving configuration: {e}")
            return False
    
    def get_config(self) -> GEMConfig:
        """Get current configuration."""
        if not self.config:
            self.config = self.load()
        return self.config
    
    def update_config(self, section: str, key: str, value: Any) -> bool:
        """Update a specific configuration value."""
        if not self.config:
            self.logger.error("No configuration loaded")
            return False
        
        try:
            section_obj = getattr(self.config, section)
            if hasattr(section_obj, key):
                setattr(section_obj, key, value)
                self.logger.info(f"Updated {section}.{key} = {value}")
                return True
            else:
                self.logger.error(f"Key '{key}' not found in section '{section}'")
                return False
        
        except AttributeError:
            self.logger.error(f"Section '{section}' not found")
            return False
    
    def get_profiles(self) -> list:
        """Get list of available profiles."""
        profiles = []
        for config_file in self.config_dir.glob("*.yaml"):
            profiles.append(config_file.stem)
        return sorted(profiles)
    
    def delete_profile(self, profile: str) -> bool:
        """Delete a configuration profile."""
        if profile == "default":
            self.logger.error("Cannot delete default profile")
            return False
        
        config_path = self.get_config_path(profile)
        
        try:
            if config_path.exists():
                config_path.unlink()
                self.logger.info(f"Profile '{profile}' deleted")
                return True
            else:
                self.logger.warning(f"Profile '{profile}' not found")
                return False
        
        except Exception as e:
            self.logger.error(f"Error deleting profile '{profile}': {e}")
            return False
    
    def copy_profile(self, source: str, target: str) -> bool:
        """Copy a configuration profile."""
        source_path = self.get_config_path(source)
        target_path = self.get_config_path(target)
        
        if not source_path.exists():
            self.logger.error(f"Source profile '{source}' not found")
            return False
        
        if target_path.exists():
            self.logger.error(f"Target profile '{target}' already exists")
            return False
        
        try:
            import shutil
            shutil.copy2(source_path, target_path)
            
            # Update profile name in the copied config
            temp_config = self.load(target)
            temp_config.general.profile_name = target
            self.config = temp_config
            self.save(target)
            
            self.logger.info(f"Profile '{source}' copied to '{target}'")
            return True
        
        except Exception as e:
            self.logger.error(f"Error copying profile: {e}")
            return False
    
    def _config_to_dict(self, config: GEMConfig) -> Dict[str, Any]:
        """Convert configuration object to dictionary."""
        return asdict(config)
    
    def _dict_to_config(self, data: Dict[str, Any]) -> GEMConfig:
        """Convert dictionary to configuration object."""
        # Handle backward compatibility for missing secondary language fields
        general_data = data.get('general', {})
        if 'secondary_language' not in general_data:
            general_data['secondary_language'] = 'pt-BR'
        
        stt_data = data.get('stt', {})
        if 'secondary_language' not in stt_data:
            stt_data['secondary_language'] = 'pt-BR'
        
        tts_data = data.get('tts', {})
        if 'secondary_language' not in tts_data:
            tts_data['secondary_language'] = 'pt-BR'
        if 'voice_style' not in tts_data:
            tts_data['voice_style'] = 'calm'
        
        llm_data = data.get('llm', {})
        if 'secondary_prompt' not in llm_data:
            llm_data['secondary_prompt'] = "Você é o GEM, um assistente de voz acessível e amigável."
        
        return GEMConfig(
            general=GeneralConfig(**general_data),
            audio=AudioConfig(**data.get('audio', {})),
            stt=STTConfig(**stt_data),
            tts=TTSConfig(**tts_data),
            llm=LLMConfig(**llm_data),
            accessibility=AccessibilityConfig(**data.get('accessibility', {})),
            health=HealthConfig(**data.get('health', {}))
        )
    
    def export_config(self, profile: str, export_path: Path) -> bool:
        """Export configuration to a file."""
        config_path = self.get_config_path(profile)
        
        if not config_path.exists():
            self.logger.error(f"Profile '{profile}' not found")
            return False
        
        try:
            import shutil
            shutil.copy2(config_path, export_path)
            self.logger.info(f"Configuration exported to {export_path}")
            return True
        
        except Exception as e:
            self.logger.error(f"Error exporting configuration: {e}")
            return False
    
    def import_config(self, import_path: Path, profile: str) -> bool:
        """Import configuration from a file."""
        if not import_path.exists():
            self.logger.error(f"Import file not found: {import_path}")
            return False
        
        try:
            # Validate the configuration first
            with open(import_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            # Try to create config object to validate structure
            test_config = self._dict_to_config(data)
            
            # If validation passes, copy the file
            config_path = self.get_config_path(profile)
            import shutil
            shutil.copy2(import_path, config_path)
            
            self.logger.info(f"Configuration imported from {import_path}")
            return True
        
        except Exception as e:
            self.logger.error(f"Error importing configuration: {e}")
            return False