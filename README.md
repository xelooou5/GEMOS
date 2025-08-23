# 💎 GEM OS - Generative Enhanced Microphone

**Assistente de Voz Acessível para toda a Humanidade**

![GEM OS Logo](https://img.shields.io/badge/GEM%20OS-v2.0.0-blue?style=for-the-badge&logo=microphone)
![Python](https://img.shields.io/badge/Python-3.8+-green?style=for-the-badge&logo=python)
![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)
![Accessibility](https://img.shields.io/badge/Accessibility-First-purple?style=for-the-badge&logo=accessibility)

## 🎯 Mission Statement

Creating an accessible, offline-first AI voice assistant for children, people with disabilities, elderly users, and everyone who needs technology that truly understands and serves humanity.

## ✨ Key Features

### 🔒 **100% Offline & Private**
- Complete privacy - no data leaves your computer
- Works without internet connection
- Local AI processing with Ollama

### ♿ **Accessibility First**
- Screen reader integration
- Voice-only operation
- High contrast mode
- Magnification tools
- Keyboard navigation support
- Multiple language support

### 🧠 **Intelligent AI**
- Local AI powered by Ollama + Phi3
- Multiple LLM provider support
- Context-aware conversations
- Adaptive learning system

### 🎤 **Advanced Voice Processing**
- Multiple STT engines (Whisper, Vosk, Google)
- Multiple TTS engines (pyttsx3, espeak, Edge TTS, gTTS)
- Wake word detection
- Noise reduction and audio processing

### 💚 **Health & Wellness**
- Medication reminders
- Health metrics tracking
- Wellness reminders
- Emergency information

### 📚 **Learning & Education**
- Adaptive learning system
- Interactive quizzes
- Progress tracking
- Personalized lessons

### 📋 **Productivity Tools**
- Task management
- Smart reminders
- Note taking
- Time tracking

## 🚀 Quick Start

### 1. Setup
```bash
# Clone and setup
git clone <repository-url>
cd gem
chmod +x gem_runner.sh

# Complete system setup
./gem_runner.sh setup
```

### 2. Run GEM OS
```bash
# Normal operation
./gem_runner.sh run

# Development mode
./gem_runner.sh dev

# Voice test
./gem_runner.sh voice-test
```

### 3. First Interaction
Say "Hey GEM" or "Oi GEM" to activate, then:
- "Que horas são?" - Get current time
- "Ajuda" - See available commands
- "Ensinar matemática" - Start learning
- "Criar lembrete" - Add reminder

## 📁 Project Structure

```
gem/
├── 🚀 gem_runner.sh          # Enhanced launcher script
├── 📋 requirements.txt       # Python dependencies
├── 💎 gem.py                # Main application
├── core/                    # Core system modules
│   ├── 🎵 audio_system.py   # Advanced audio management
│   ├── ⚙️ config_manager.py # Configuration management
│   ├── 🎤 stt_module.py     # Speech-to-text engine
│   ├── 🗣️ tts_module.py     # Text-to-speech engine
│   ├── 🤖 llm_handler.py    # AI integration
│   ├── 🎯 command_executor.py # Command processing
│   └── 📊 system_monitor.py # System health monitoring
├── features/                # Feature modules
│   ├── ♿ accessibility_tools.py # Accessibility features
│   ├── 💚 health_assistant.py   # Health & wellness
│   ├── 📚 learning_tools.py     # Educational tools
│   └── 📋 productivity_tools.py # Productivity features
├── data/                    # Data storage
│   ├── models/             # AI models
│   ├── database/           # User data
│   ├── logs/               # Application logs
│   └── backups/            # Data backups
└── tests/                  # Test suite
```

## 🛠️ System Requirements

### Minimum Requirements
- **OS**: Linux, macOS, Windows
- **Python**: 3.8+
- **RAM**: 4GB
- **Storage**: 2GB free space
- **Audio**: Microphone and speakers

### Recommended
- **RAM**: 8GB+
- **CPU**: Multi-core processor
- **Audio**: Quality microphone for better recognition

## 🔧 Configuration

GEM OS uses YAML configuration files stored in `~/.gem/config/`:

```yaml
# Example configuration
general:
  language: "pt-BR"
  wake_words: ["hey gem", "oi gem"]
  offline_mode: true

audio:
  sample_rate: 16000
  noise_reduction: true
  
stt:
  engine: "whisper"
  model: "base"
  
tts:
  engine: "pyttsx3"
  rate: 150
  
accessibility:
  screen_reader_support: true
  high_contrast_mode: false
  voice_commands_only: false
```

## 🎮 Usage Examples

### Basic Commands
```
"Que horas são?"              # Get current time
"Que dia é hoje?"             # Get current date
"Ajuda"                       # Show available commands
"Desligar"                    # Shutdown system
```

### Accessibility
```
"Ler tela"                    # Read screen content
"Aumentar texto"              # Zoom in
"Alto contraste"              # Toggle high contrast
"Modo emergência"             # Emergency accessibility mode
```

### Health & Wellness
```
"Lembrar medicamento aspirina às 8 horas"
"Registrar pressão 120 por 80"
"Como está minha saúde?"
"Informações de emergência"
```

### Learning
```
"Ensinar matemática"          # Start math lesson
"Quiz de português"           # Portuguese quiz
"Praticar inglês"            # English practice
"Meu progresso em ciências"   # Learning progress
```

### Productivity
```
"Criar tarefa comprar leite"  # Create task
"Listar tarefas"             # List tasks
"Lembrete em 30 minutos"     # Set reminder
"Criar nota reunião"         # Create note
```

## 🔌 Extensibility

### Adding Custom Commands
```python
# In command_executor.py
self.register_command(
    patterns=[r"meu comando (.+)"],
    handler=self._handle_my_command,
    description="My custom command",
    category="custom"
)
```

### Custom TTS Engine
```python
# Create new TTS engine
class MyTTSEngine(TTSEngine):
    async def speak(self, text: str) -> bool:
        # Your implementation
        pass
```

## 🧪 Testing

```bash
# Run all tests
./gem_runner.sh test

# Test specific components
python -m pytest tests/test_audio.py
python -m pytest tests/test_stt.py
```

## 🔍 Troubleshooting

### Common Issues

**Audio not working:**
```bash
# Check audio devices
./gem_runner.sh audio-test

# Install audio dependencies (Linux)
sudo apt-get install portaudio19-dev alsa-utils
```

**STT not recognizing speech:**
- Check microphone permissions
- Adjust energy threshold in config
- Try different STT engine

**TTS not speaking:**
```bash
# Test TTS
./gem_runner.sh voice-test

# Install TTS dependencies
sudo apt-get install espeak festival
```

**Ollama connection failed:**
```bash
# Install and start Ollama
curl -fsSL https://ollama.ai/install.sh | sh
ollama serve
ollama pull phi3:mini
```

## 🤝 Contributing

We welcome contributions! Please see our contributing guidelines:

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

### Development Setup
```bash
# Setup development environment
./gem_runner.sh setup
python -m pip install -e .

# Run in development mode
./gem_runner.sh dev --debug
```

## 📊 Performance & Monitoring

GEM OS includes built-in system monitoring:

- **CPU Usage**: Tracks system performance
- **Memory Usage**: Monitors memory consumption
- **Audio Quality**: Analyzes audio input/output
- **Response Times**: Measures system responsiveness
- **Error Tracking**: Logs and analyzes errors

Access monitoring data:
```
"Status do sistema"           # System health
"Estatísticas de uso"         # Usage statistics
"Relatório de performance"    # Performance report
```

## 🔐 Privacy & Security

- **100% Offline**: No data transmitted to external servers
- **Local Processing**: All AI processing happens locally
- **Encrypted Storage**: User data encrypted at rest
- **No Telemetry**: No usage data collection
- **Open Source**: Full transparency in code

## 🌍 Internationalization

Currently supported languages:
- 🇧🇷 Portuguese (Brazil) - Primary
- 🇺🇸 English - Secondary
- 🇪🇸 Spanish - Planned
- 🇫🇷 French - Planned

## 📈 Roadmap

### Version 2.1 (Next Release)
- [ ] Mobile app companion
- [ ] Advanced voice training
- [ ] Custom wake word creation
- [ ] Plugin marketplace

### Version 2.2 (Future)
- [ ] Multi-user support
- [ ] Advanced health analytics
- [ ] Smart home integration
- [ ] Gesture recognition

### Version 3.0 (Long-term)
- [ ] Emotional intelligence
- [ ] Advanced learning AI
- [ ] Predictive assistance
- [ ] IoT ecosystem integration

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Ollama Team** - Local AI infrastructure
- **OpenAI Whisper** - Speech recognition
- **Accessibility Community** - Guidance and feedback
- **Open Source Contributors** - Various libraries and tools

## 📞 Support

- **Documentation**: [Wiki](wiki-url)
- **Issues**: [GitHub Issues](issues-url)
- **Discussions**: [GitHub Discussions](discussions-url)
- **Email**: support@gem-os.org

## 🌟 Star History

[![Star History Chart](https://api.star-history.com/svg?repos=gem-os/gem&type=Date)](https://star-history.com/#gem-os/gem&Date)

---

**Made with ❤️ for accessibility and humanity**

*GEM OS - Where technology serves everyone, everywhere, every time.*