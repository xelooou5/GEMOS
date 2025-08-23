#!/bin/bash
# 💎 GEM OS - Enhanced Launcher Script
# Assistente de Voz Acessível para toda a Humanidade
# Version: 2.0.0 - Complete Deployment Strategy

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Project paths
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="$PROJECT_ROOT/.venv"
PYTHON_CMD=""

# Logging function
log() {
    echo -e "${CYAN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Detect system and Python
detect_system() {
    log "🔍 Detecting system configuration..."
    
    # Detect OS
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="linux"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        OS="windows"
    else
        OS="unknown"
    fi
    
    # Find Python
    for cmd in python3.11 python3.10 python3.9 python3.8 python3 python; do
        if command -v "$cmd" &> /dev/null; then
            PYTHON_CMD="$cmd"
            break
        fi
    done
    
    if [[ -z "$PYTHON_CMD" ]]; then
        error "Python 3.8+ not found. Please install Python."
        exit 1
    fi
    
    PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | cut -d' ' -f2)
    success "System: $OS, Python: $PYTHON_VERSION"
}

# Activate virtual environment based on OS
activate_venv() {
    if [[ "$OS" == "windows" ]]; then
        source "$VENV_PATH/Scripts/activate"
    else
        source "$VENV_PATH/bin/activate"
    fi
}

# Create virtual environment
setup_venv() {
    log "🐍 Setting up Python virtual environment..."
    
    if [[ ! -d "$VENV_PATH" ]]; then
        $PYTHON_CMD -m venv "$VENV_PATH"
        success "Virtual environment created"
    else
        log "Virtual environment already exists"
    fi
    
    # Activate virtual environment
    activate_venv
    
    # Upgrade pip
    pip install --upgrade pip setuptools wheel
}

# Install system dependencies
install_system_deps() {
    log "📦 Installing system dependencies..."
    
    case $OS in
        "linux")
            if command -v apt-get &> /dev/null; then
                sudo apt-get update
                sudo apt-get install -y \
                    portaudio19-dev \
                    espeak espeak-data \
                    festival festvox-kallpc16k \
                    alsa-utils \
                    ffmpeg \
                    build-essential \
                    python3-dev \
                    libasound2-dev
            elif command -v yum &> /dev/null; then
                sudo yum install -y \
                    portaudio-devel \
                    espeak \
                    festival \
                    alsa-lib-devel \
                    ffmpeg \
                    gcc gcc-c++ \
                    python3-devel
            fi
            ;;
        "macos")
            if command -v brew &> /dev/null; then
                brew install portaudio espeak festival ffmpeg
            else
                warning "Homebrew not found. Please install system dependencies manually."
            fi
            ;;
        "windows")
            warning "Windows detected. Please ensure you have the required audio libraries."
            ;;
    esac
}

# Install Python dependencies
install_python_deps() {
    log "🔧 Installing Python dependencies..."
    
    activate_venv
    
    # Install requirements
    if [[ -f "$PROJECT_ROOT/requirements.txt" ]]; then
        pip install -r "$PROJECT_ROOT/requirements.txt"
        success "Python dependencies installed"
    else
        error "requirements.txt not found"
        exit 1
    fi
}

# Setup Ollama
setup_ollama() {
    log "🤖 Setting up Ollama..."
    
    if ! command -v ollama &> /dev/null; then
        warning "Ollama not found. Installing..."
        curl -fsSL https://ollama.ai/install.sh | sh
    fi
    
    # Start Ollama service
    if ! pgrep -x "ollama" > /dev/null; then
        log "Starting Ollama service in the background..."
        ollama serve &
        OLLAMA_PID=$!
        # Ensure Ollama is terminated if the script exits prematurely during setup
        trap "log 'Stopping Ollama service...'; kill $OLLAMA_PID 2>/dev/null" EXIT

        log "Waiting for Ollama to be ready..."
        # Wait up to 30 seconds for the service to respond
        for i in {1..30}; do
            if curl --silent --output /dev/null http://localhost:11434; then
                success "Ollama service is running."
                break
            fi
            sleep 1
        done
        # Remove the trap if Ollama started successfully and we are proceeding
        trap - EXIT
    fi
    
    # Pull required models
    log "Downloading AI models..."
    ollama pull phi3:mini
    success "Ollama setup complete"
}

# Create directory structure
create_directories() {
    log "📁 Creating directory structure..."
    
    mkdir -p "$PROJECT_ROOT"/{core,features,engines,bridge,tests,scripts,docs,data/{models,database,logs,backups}}
    
    # Create __init__.py files
    touch "$PROJECT_ROOT/core/__init__.py"
    touch "$PROJECT_ROOT/features/__init__.py"
    touch "$PROJECT_ROOT/engines/__init__.py"
    touch "$PROJECT_ROOT/bridge/__init__.py"
    touch "$PROJECT_ROOT/tests/__init__.py"
    
    success "Directory structure created"
}

# Run tests
run_tests() {
    log "🧪 Running tests..."
    
    activate_venv
    cd "$PROJECT_ROOT"
    
    if [[ -d "tests" ]]; then
        python -m pytest tests/ -v
    else
        warning "No tests directory found"
    fi
}

# Start GEM OS
start_gem() {
    log "🚀 Starting GEM OS..."
    
    activate_venv
    cd "$PROJECT_ROOT"
    
    python gem.py "$@"
}

# Development mode
dev_mode() {
    log "🔧 Starting development mode..."
    
    activate_venv
    cd "$PROJECT_ROOT"
    
    python gem.py --debug "$@"
}

# Backup user data
backup_data() {
    log "💾 Backing up user data..."
    
    BACKUP_DIR="$PROJECT_ROOT/data/backups/backup_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP_DIR"
    
    if [[ -d "$PROJECT_ROOT/data/database" ]]; then
        cp -r "$PROJECT_ROOT/data/database" "$BACKUP_DIR/"
    fi
    
    if [[ -d "$PROJECT_ROOT/data/models" ]]; then
        cp -r "$PROJECT_ROOT/data/models" "$BACKUP_DIR/"
    fi
    
    success "Backup created at $BACKUP_DIR"
}

# Show help
show_help() {
    echo -e "${PURPLE}💎 GEM OS - Enhanced Launcher${NC}"
    echo -e "${CYAN}Assistente de Voz Acessível para toda a Humanidade${NC}"
    echo ""
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  setup          - Complete system setup"
    echo "  run            - Start GEM OS"
    echo "  dev            - Start in development mode"
    echo "  test           - Run test suite"
    echo "  backup         - Backup user data"
    echo "  voice-test     - Test voice synthesis"
    echo "  audio-test     - Test audio capture"
    echo "  help           - Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 setup       # First-time setup"
    echo "  $0 run         # Normal operation"
    echo "  $0 dev --debug # Development with debug"
}

# Main execution
main() {
    echo -e "${PURPLE}"
    echo "💎 GEM OS - Generative Enhanced Microphone"
    echo "🎯 Assistente de Voz Acessível para toda a Humanidade"
    echo -e "${NC}"
    
    detect_system
    
    case "${1:-run}" in
        "setup")
            create_directories
            setup_venv
            install_system_deps
            install_python_deps
            setup_ollama
            success "🎉 GEM OS setup complete! Run './gem_runner.sh run' to start."
            ;;
        "run")
            shift
            start_gem "$@"
            ;;
        "dev")
            shift
            dev_mode "$@"
            ;;
        "test")
            run_tests
            ;;
        "backup")
            backup_data
            ;;
        "voice-test")
            start_gem --voice-test
            ;;
        "audio-test")
            start_gem --audio-test
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            error "Unknown command: $1"
            show_help
            exit 1
            ;;
    esac
}

# Execute main function
main "$@"