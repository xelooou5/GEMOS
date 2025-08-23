#!/usr/bin/env python3
"""
💎 GEM OS - Voice Training Module
Voice model training and customization
"""

import logging
import json
import numpy as np
import os
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import threading

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# =============================================================================
# Dataclasses
# =============================================================================

@dataclass
class VoiceProfile:
    """Voice profile data structure"""
    user_id: str
    name: str
    created_date: datetime
    sample_count: int = 0
    training_accuracy: float = 0.0
    is_active: bool = False
    voice_characteristics: Dict = None
    
    def __post_init__(self):
        if self.voice_characteristics is None:
            self.voice_characteristics = {}
    
    def to_dict(self):
        """Convert dataclass to dictionary for JSON serialization"""
        d = asdict(self)
        d['created_date'] = self.created_date.isoformat()
        return d
        
    @classmethod
    def from_dict(cls, d):
        """Create dataclass instance from a dictionary"""
        d['created_date'] = datetime.fromisoformat(d['created_date'])
        return cls(**d)

@dataclass
class TrainingSession:
    """Voice training session data"""
    session_id: str
    user_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    samples_recorded: int = 0
    
    def to_dict(self):
        d = asdict(self)
        d['start_time'] = self.start_time.isoformat()
        if self.end_time:
            d['end_time'] = self.end_time.isoformat()
        return d

# =============================================================================
# Main Class
# =============================================================================

class VoiceTraining:
    """
    Manages voice profile creation, training, and activation.
    """
    
    def __init__(self, data_dir: str = "data"):
        self.logger = logging.getLogger(__name__)
        self.data_dir = data_dir
        self.profile_file = os.path.join(data_dir, "voice_profiles.json")
        self.profiles: Dict[str, VoiceProfile] = {}
        self.current_session: Optional[TrainingSession] = None
        self.audio_samples: List[bytes] = []
        
        os.makedirs(self.data_dir, exist_ok=True)
        self._load_profiles()
        
    def _load_profiles(self) -> None:
        """Load voice profiles from a JSON file."""
        if not os.path.exists(self.profile_file):
            self.logger.info("Voice profile file not found. Starting with empty profiles.")
            return
            
        try:
            with open(self.profile_file, 'r') as f:
                data = json.load(f)
                self.profiles = {k: VoiceProfile.from_dict(v) for k, v in data.items()}
            self.logger.info(f"Loaded {len(self.profiles)} voice profiles.")
        except (IOError, json.JSONDecodeError) as e:
            self.logger.error(f"Failed to load profiles: {e}")
            self.profiles = {}

    def _save_profiles(self) -> None:
        """Save voice profiles to a JSON file."""
        try:
            data = {k: v.to_dict() for k, v in self.profiles.items()}
            with open(self.profile_file, 'w') as f:
                json.dump(data, f, indent=2)
            self.logger.info("Voice profiles saved successfully.")
        except IOError as e:
            self.logger.error(f"Failed to save profiles: {e}")

    # ------------------------------------------------------------------- Public API
    
    def create_profile(self, user_id: str, name: str) -> str:
        """Create a new voice profile for a user."""
        if user_id in self.profiles:
            return f"❌ Profile for user '{user_id}' already exists."
        
        new_profile = VoiceProfile(
            user_id=user_id,
            name=name,
            created_date=datetime.now(),
        )
        self.profiles[user_id] = new_profile
        self._save_profiles()
        return f"✅ Profile '{name}' created for user '{user_id}'."

    def get_voice_profiles(self) -> List[Dict]:
        """List all available voice profiles."""
        return [p.to_dict() for p in self.profiles.values()]

    def start_training_session(self, user_id: str) -> str:
        """Begin a new voice training session."""
        if user_id not in self.profiles:
            return f"❌ Cannot start training: Profile for user '{user_id}' not found."
            
        if self.current_session and self.current_session.user_id == user_id:
            return f"⚠️ A training session for user '{user_id}' is already active."
            
        session_id = f"session_{int(time.time())}"
        self.current_session = TrainingSession(
            session_id=session_id,
            user_id=user_id,
            start_time=datetime.now(),
        )
        self.audio_samples = []
        return f"✅ Training session '{session_id}' started for user '{user_id}'."

    def record_sample(self, pcm_data: Optional[bytes] = None) -> str:
        """
        Record a voice sample and add it to the current session.
        Simulated by just incrementing the count for this example.
        """
        if not self.current_session:
            return "❌ No active training session. Please start one first."
            
        # Simulate recording a sample
        if pcm_data is None:
            pcm_data = os.urandom(1024)  # Placeholder for real audio data
            
        self.audio_samples.append(pcm_data)
        self.current_session.samples_recorded += 1
        
        # Update profile sample count
        profile = self.profiles.get(self.current_session.user_id)
        if profile:
            profile.sample_count = self.current_session.samples_recorded
            
        return f"🎙️ Sample recorded. Total samples: {self.current_session.samples_recorded}"

    def end_training_session(self) -> str:
        """End the current voice training session."""
        if not self.current_session:
            return "❌ No active training session to end."
            
        self.current_session.end_time = datetime.now()
        user_id = self.current_session.user_id
        
        # Save profile updates
        self._save_profiles()
        
        self.current_session = None
        self.audio_samples = []
        return f"✅ Training session for user '{user_id}' ended. Samples recorded: {self.profiles[user_id].sample_count}"

    def get_training_status(self) -> Dict:
        """Get the current status of the active training session."""
        if not self.current_session:
            return {"status": "inactive"}
            
        return {
            "status": "active",
            "user_id": self.current_session.user_id,
            "session_id": self.current_session.session_id,
            "samples_recorded": self.current_session.samples_recorded,
            "start_time": self.current_session.start_time.isoformat(),
        }

    def train_model(self, user_id: str) -> str:
        """Train a new voice model using the recorded samples."""
        if user_id not in self.profiles:
            return f"❌ Profile for user '{user_id}' not found."
        
        profile = self.profiles[user_id]
        if profile.sample_count < 100:
            return f"⚠️ Insufficient samples. Need at least 100 to train, but only have {profile.sample_count}."
            
        self.logger.info(f"Training voice model for user '{user_id}' with {profile.sample_count} samples...")
        
        # Simulate a training process
        time.sleep(2)
        
        # Simulate training accuracy
        simulated_accuracy = min(0.99, 0.5 + (profile.sample_count / 2000.0))
        profile.training_accuracy = simulated_accuracy
        
        self._save_profiles()
        return f"✅ Model trained successfully. Accuracy: {simulated_accuracy:.2f}"

    def activate_profile(self, user_id: str) -> str:
        """Set a voice profile as the active one for recognition."""
        if user_id not in self.profiles:
            return f"❌ Profile for user '{user_id}' not found."
            
        # Deactivate all other profiles
        for uid in self.profiles:
            self.profiles[uid].is_active = False
            
        self.profiles[user_id].is_active = True
        self._save_profiles()
        return f"✅ Profile '{self.profiles[user_id].name}' activated."

    def get_training_tips(self) -> str:
        """Provide tips for effective voice training."""
        tips = [
            "Record in a quiet environment to minimize background noise.",
            "Speak clearly and at a consistent pace during training.",
            "Record a variety of phrases, not just a single word.",
            "Ensure your microphone is close to your mouth but not so close that it picks up breathing sounds.",
        ]
        import random
        return f"💡 Voice Training Tip: {random.choice(tips)}"

    def shutdown(self) -> None:
        """Graceful shutdown"""
        self._save_profiles()
        self.logger.info("VoiceTraining module shut down.")

# =============================================================================
# CLI Test
# =============================================================================

if __name__ == "__main__":
    print("Running VoiceTraining module test...")
    trainer = VoiceTraining()
    
    # 1. Create a voice profile
    print(trainer.create_profile(user_id="user123", name="Marcelo"))
    
    # 2. List profiles
    print("\n--- Getting voice profiles ---")
    print(trainer.get_voice_profiles())
    
    # 3. Start a new training session
    print("\n--- Starting a training session ---")
    print(trainer.start_training_session(user_id="user123"))

    # 4. Record samples in a loop
    print("\n--- Recording voice samples (simulated) ---")
    for i in range(105):
        time.sleep(0.01) # Simulate recording time
        trainer.record_sample()
    
    # Check status mid-session
    print("\n--- Getting training status ---")
    print(trainer.get_training_status())
    
    # 5. End the training session
    print("\n--- Ending the training session ---")
    print(trainer.end_training_session())
    
    # 6. Check the updated profile
    print("\n--- Re-checking voice profiles ---")
    print(trainer.get_voice_profiles())
    
    # 7. Train the voice model
    print("\n--- Training the voice model ---")
    print(trainer.train_model(user_id="user123"))
    
    # Check the final profile accuracy
    print("\n--- Final profile check ---")
    print(trainer.get_voice_profiles())

    # 8. Activate the profile
    print("\n--- Activating the profile ---")
    print(trainer.activate_profile(user_id="user123"))
    
    # 9. Get training tips
    print("\n--- Getting training tips ---")
    print(trainer.get_training_tips())
    
    # 10. Delete the profile (not implemented, but shows the next logical step)
    print("\n--- Deleting the profile ---")
    print("Functionality not implemented yet, but would be next.")
