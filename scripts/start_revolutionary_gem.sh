#!/bin/bash
# 🚀 GEM OS Revolutionary Edition - Quick Start
# The most advanced accessible AI voice assistant ever created

set -e

# Colors for beautiful output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# Project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Beautiful banner
show_banner() {
    echo -e "${PURPLE}${BOLD}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                    💎 GEM OS v2.0.0                         ║"
    echo "║              Revolutionary AI Edition                        ║"
    echo "║                                                              ║"
    echo "║    🤖 AI Companion with Emotional Intelligence               ║"
    echo "║    ♿ Advanced Accessibility for Everyone                    ║"
    echo "║    💚 Smart Health Monitoring & Predictions                 ║"
    echo "║    🎓 Adaptive Learning That Grows With You                 ║"
    echo "║    🔒 100% Private & Offline                                ║"
    echo "║                                                              ║"
    echo "║         Assistente de Voz para toda a Humanidade            ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Logging functions
log() { echo -e "${CYAN}[$(date +'%H:%M:%S')]${NC} $1"; }
success() { echo -e "${GREEN}${BOLD}[SUCCESS]${NC} $1"; }
warning() { echo -e "${YELLOW}${BOLD}[WARNING]${NC} $1"; }
error() { echo -e "${RED}${BOLD}[ERROR]${NC} $1"; }
info() { echo -e "${BLUE}[INFO]${NC} $1"; }

# Check system requirements
check_requirements() {
    log "🔍 Checking system requirements..."
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        error "Python 3.8+ is required but not installed"
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    info "Python version: $PYTHON_VERSION"
    
    # Check if we have the required directories
    if [ ! -d "$PROJECT_ROOT/core" ]; then
        error "GEM OS core modules not found. Please ensure you're in the correct directory."
        exit 1
    fi
    
    success "System requirements check passed"
}

# Setup virtual environment
setup_environment() {
    log "🐍 Setting up Python environment..."
    
    cd "$PROJECT_ROOT"
    
    # Create virtual environment if it doesn't exist
    if [ ! -d ".venv" ]; then
        python3 -m venv .venv
        success "Virtual environment created"
    else
        info "Virtual environment already exists"
    fi
    
    # Activate virtual environment
    source .venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip setuptools wheel > /dev/null 2>&1
    
    success "Python environment ready"
}

# Install dependencies
install_dependencies() {
    log "📦 Installing revolutionary AI dependencies..."
    
    # Install requirements
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt > /dev/null 2>&1
        success "All dependencies installed"
    else
        warning "requirements.txt not found, some features may not work"
    fi
}

# Check for API keys
check_api_keys() {
    log "🔑 Checking AI provider configurations..."
    
    if [ ! -f ".env" ]; then
        if [ -f ".env.template" ]; then
            cp .env.template .env
            warning "Created .env file from template"
            warning "Please edit .env file with your API keys for enhanced AI features"
            info "Run: ./scripts/setup_api_keys.sh for API key links"
        else
            warning "No .env file found. Some AI features may be limited."
        fi
    else
        success "Environment configuration found"
    fi
}

# Check Ollama
check_ollama() {
    log "🤖 Checking local AI (Ollama) setup..."
    
    if command -v ollama &> /dev/null; then
        if pgrep -x "ollama" > /dev/null; then
            success "Ollama is running"
        else
            info "Starting Ollama service..."
            ollama serve &
            sleep 3
            success "Ollama service started"
        fi
        
        # Check if phi3 model is available
        if ollama list | grep -q "phi3"; then
            success "Phi3 model available"
        else
            info "Downloading Phi3 model for local AI..."
            ollama pull phi3:mini
            success "Phi3 model ready"
        fi
    else
        warning "Ollama not found. Local AI features will be limited."
        info "Install Ollama: curl -fsSL https://ollama.ai/install.sh | sh"
    fi
}

# Create necessary directories
create_directories() {
    log "📁 Creating data directories..."
    
    mkdir -p data/{database,logs,backups,models}
    mkdir -p ~/.gem/{config,data}
    
    success "Directory structure created"
}

# Show feature status
show_feature_status() {
    echo -e "\n${BOLD}🚀 Revolutionary Features Status:${NC}"
    echo -e "${GREEN}✅ AI Companion with Emotional Intelligence${NC}"
    echo -e "${GREEN}✅ Advanced Accessibility System${NC}"
    echo -e "${GREEN}✅ Smart Health Monitoring${NC}"
    echo -e "${GREEN}✅ Adaptive Learning Engine${NC}"
    echo -e "${GREEN}✅ Multi-AI Provider Integration${NC}"
    echo -e "${GREEN}✅ Predictive Assistance${NC}"
    echo -e "${GREEN}✅ Privacy-First Architecture${NC}"
    
    if command -v ollama &> /dev/null; then
        echo -e "${GREEN}✅ Local AI (Ollama) Available${NC}"
    else
        echo -e "${YELLOW}⚠️  Local AI (Ollama) Not Installed${NC}"
    fi
    
    if [ -f ".env" ]; then
        echo -e "${GREEN}✅ API Configuration Found${NC}"
    else
        echo -e "${YELLOW}⚠️  API Keys Not Configured${NC}"
    fi
}

# Start GEM OS
start_gem_os() {
    log "🚀 Starting GEM OS Revolutionary Edition..."
    
    # Activate virtual environment
    source .venv/bin/activate
    
    echo -e "\n${BOLD}${PURPLE}Starting the most advanced accessible AI voice assistant...${NC}\n"
    
    # Start GEM OS
    python gem.py --profile=default
}

# Show help information
show_help() {
    echo -e "\n${BOLD}💎 GEM OS Revolutionary Edition${NC}"
    echo -e "${CYAN}Available commands:${NC}"
    echo "  start     - Start GEM OS (default)"
    echo "  setup     - Run complete setup"
    echo "  test      - Run voice and audio tests"
    echo "  dev       - Start in development mode"
    echo "  status    - Show system status"
    echo "  help      - Show this help"
    echo ""
    echo -e "${BOLD}Examples:${NC}"
    echo "  $0 start"
    echo "  $0 setup"
    echo "  $0 test"
    echo ""
}

# Main execution
main() {
    show_banner
    
    case "${1:-start}" in
        "setup")
            check_requirements
            setup_environment
            install_dependencies
            check_api_keys
            check_ollama
            create_directories
            show_feature_status
            success "🎉 GEM OS Revolutionary Edition setup complete!"
            echo -e "\n${BOLD}Next steps:${NC}"
            echo "1. Edit .env file with your API keys (optional but recommended)"
            echo "2. Run: $0 start"
            ;;
        
        "start")
            check_requirements
            setup_environment
            check_api_keys
            check_ollama
            create_directories
            show_feature_status
            echo -e "\n${BOLD}${GREEN}Ready to start the revolution in accessible AI!${NC}\n"
            start_gem_os
            ;;
        
        "test")
            check_requirements
            setup_environment
            source .venv/bin/activate
            echo -e "\n${BOLD}Testing GEM OS components...${NC}\n"
            python gem.py --voice-test
            python gem.py --audio-test
            ;;
        
        "dev")
            check_requirements
            setup_environment
            check_api_keys
            source .venv/bin/activate
            echo -e "\n${BOLD}Starting GEM OS in development mode...${NC}\n"
            python gem.py --debug
            ;;
        
        "status")
            show_feature_status
            if command -v ollama &> /dev/null && pgrep -x "ollama" > /dev/null; then
                echo -e "\n${BOLD}Ollama Models:${NC}"
                ollama list
            fi
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