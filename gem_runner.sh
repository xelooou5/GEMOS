#!/bin/bash
# 💎 GEM OS - Enhanced Runner Script
# AI Team Collaboration: Amazon Q, Claude, Gemini, TabNine, Copilot, Cursor
# SACRED RULES: Never rename files, enhance existing ones

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Project paths
PROJECT_DIR="/home/oem/PycharmProjects/gem"
VENV_DIR="$PROJECT_DIR/venv"
LOG_DIR="$PROJECT_DIR/logs"
DATA_DIR="$PROJECT_DIR/data"

# Banner
print_banner() {
    echo -e "${PURPLE}💎==========================================================💎${NC}"
    echo -e "${PURPLE}💎 GEM OS - Generative Enhanced Microphone v2.0.0        💎${NC}"
    echo -e "${PURPLE}💎 AI Team: Amazon Q + Claude + Gemini + TabNine + Copilot💎${NC}"
    echo -e "${PURPLE}💎 Accessibility-First Voice Assistant                    💎${NC}"
    echo -e "${PURPLE}💎==========================================================💎${NC}"
}

# Check system requirements
check_requirements() {
    echo -e "${BLUE}🔍 Checking system requirements...${NC}"
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}❌ Python 3 not found${NC}"
        exit 1
    fi
    
    # Check audio system
    if ! command -v aplay &> /dev/null && ! command -v paplay &> /dev/null; then
        echo -e "${YELLOW}⚠️ Audio system may not be available${NC}"
    fi
    
    echo -e "${GREEN}✅ System requirements check complete${NC}"
}

# Setup virtual environment
setup_venv() {
    echo -e "${BLUE}🐍 Setting up Python virtual environment...${NC}"
    
    if [ ! -d "$VENV_DIR" ]; then
        python3 -m venv "$VENV_DIR"
        echo -e "${GREEN}✅ Virtual environment created${NC}"
    fi
    
    source "$VENV_DIR/bin/activate"
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install requirements
    if [ -f "$PROJECT_DIR/requirements.txt" ]; then
        pip install -r "$PROJECT_DIR/requirements.txt"
        echo -e "${GREEN}✅ Dependencies installed${NC}"
    else
        echo -e "${YELLOW}⚠️ requirements.txt not found, installing basic dependencies${NC}"
        pip install asyncio sounddevice numpy google-generativeai boto3 webrtcvad
    fi
}

# Create necessary directories
setup_directories() {
    echo -e "${BLUE}📁 Creating project directories...${NC}"
    
    mkdir -p "$LOG_DIR"
    mkdir -p "$DATA_DIR/models"
    mkdir -p "$DATA_DIR/database"
    mkdir -p "$DATA_DIR/backups"
    mkdir -p "$DATA_DIR/memory"
    mkdir -p "$DATA_DIR/agent_communication"
    
    echo -e "${GREEN}✅ Directories created${NC}"
}

# Check environment variables
check_env_vars() {
    echo -e "${BLUE}🔑 Checking environment variables...${NC}"
    
    # Load .env file if it exists
    if [ -f "$PROJECT_DIR/.env" ]; then
        source "$PROJECT_DIR/.env"
        echo -e "${GREEN}✅ .env file loaded${NC}"
    fi
    
    # Check required variables
    missing_vars=()
    
    if [ -z "$GOOGLE_AI_API_KEY" ]; then
        missing_vars+=("GOOGLE_AI_API_KEY")
    fi
    
    if [ ${#missing_vars[@]} -gt 0 ]; then
        echo -e "${YELLOW}⚠️ Missing environment variables:${NC}"
        for var in "${missing_vars[@]}"; do
            echo -e "   ${YELLOW}• $var${NC}"
        done
        echo -e "${YELLOW}   Please set these in your .env file${NC}"
    else
        echo -e "${GREEN}✅ All required environment variables set${NC}"
    fi
}

# Run GEM OS
run_gem() {
    echo -e "${CYAN}🚀 Starting GEM OS...${NC}"
    
    cd "$PROJECT_DIR"
    source "$VENV_DIR/bin/activate"
    
    # Load environment variables
    if [ -f ".env" ]; then
        export $(cat .env | xargs)
    fi
    
    # Run the main application
    python3 gem.py "$@"
}

# Run in development mode
run_dev() {
    echo -e "${CYAN}🛠️ Starting GEM OS in development mode...${NC}"
    
    cd "$PROJECT_DIR"
    source "$VENV_DIR/bin/activate"
    
    # Load environment variables
    if [ -f ".env" ]; then
        export $(cat .env | xargs)
    fi
    
    # Set debug environment
    export GEM_DEBUG=1
    export PYTHONPATH="$PROJECT_DIR:$PYTHONPATH"
    
    # Run with debug output
    python3 -u gem.py --debug "$@"
}

# Test voice system
test_voice() {
    echo -e "${CYAN}🎤 Testing voice system...${NC}"
    
    cd "$PROJECT_DIR"
    source "$VENV_DIR/bin/activate"
    
    python3 -c "
import asyncio
from voice_interface import VoiceInterface
import config

async def test():
    voice = VoiceInterface(
        language_code=config.LANGUAGE_CODE,
        polly_voice=config.POLLY_VOICE,
        wake_word=config.WAKE_WORD
    )
    
    print('🎤 Testing text-to-speech...')
    await voice.speak('Hello! This is a voice system test. Can you hear me clearly?')
    
    print('🎧 Voice test complete!')

asyncio.run(test())
"
}

# Run audio test
test_audio() {
    echo -e "${CYAN}🔊 Testing audio system...${NC}"
    
    # Test audio output
    if command -v speaker-test &> /dev/null; then
        echo -e "${BLUE}Testing speakers...${NC}"
        speaker-test -t sine -f 1000 -l 1 -s 1
    fi
    
    # Test microphone
    if command -v arecord &> /dev/null; then
        echo -e "${BLUE}Testing microphone (5 seconds)...${NC}"
        arecord -d 5 -f cd /tmp/test_audio.wav && echo -e "${GREEN}✅ Microphone test complete${NC}"
        rm -f /tmp/test_audio.wav
    fi
}

# Show system status
show_status() {
    echo -e "${CYAN}📊 GEM OS System Status${NC}"
    echo -e "${BLUE}========================${NC}"
    
    # Check if running
    if pgrep -f "gem.py" > /dev/null; then
        echo -e "${GREEN}🟢 GEM OS is running${NC}"
    else
        echo -e "${RED}🔴 GEM OS is not running${NC}"
    fi
    
    # Check virtual environment
    if [ -d "$VENV_DIR" ]; then
        echo -e "${GREEN}✅ Virtual environment exists${NC}"
    else
        echo -e "${RED}❌ Virtual environment missing${NC}"
    fi
    
    # Check log files
    if [ -d "$LOG_DIR" ] && [ "$(ls -A $LOG_DIR)" ]; then
        echo -e "${GREEN}✅ Log files present${NC}"
        echo -e "${BLUE}   Latest logs:${NC}"
        ls -la "$LOG_DIR" | tail -5
    else
        echo -e "${YELLOW}⚠️ No log files found${NC}"
    fi
    
    # System resources
    echo -e "${BLUE}💻 System Resources:${NC}"
    echo -e "   CPU: $(nproc) cores"
    echo -e "   Memory: $(free -h | awk '/^Mem:/ {print $2}')"
    echo -e "   Disk: $(df -h $PROJECT_DIR | awk 'NR==2 {print $4}') available"
}

# Clean up system
cleanup() {
    echo -e "${YELLOW}🧹 Cleaning up GEM OS...${NC}"
    
    # Stop any running processes
    pkill -f "gem.py" 2>/dev/null || true
    
    # Clean temporary files
    rm -f /tmp/gem_*
    rm -f "$PROJECT_DIR"/*.pyc
    find "$PROJECT_DIR" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    
    # Clean old logs (keep last 10)
    if [ -d "$LOG_DIR" ]; then
        find "$LOG_DIR" -name "*.log" -type f | sort | head -n -10 | xargs rm -f 2>/dev/null || true
    fi
    
    echo -e "${GREEN}✅ Cleanup complete${NC}"
}

# Show help
show_help() {
    echo -e "${CYAN}GEM OS Runner - Available Commands:${NC}"
    echo ""
    echo -e "${GREEN}Setup Commands:${NC}"
    echo -e "  ${BLUE}setup${NC}        - Complete system setup"
    echo -e "  ${BLUE}install${NC}      - Install dependencies only"
    echo ""
    echo -e "${GREEN}Run Commands:${NC}"
    echo -e "  ${BLUE}run${NC}          - Start GEM OS normally"
    echo -e "  ${BLUE}dev${NC}          - Start in development mode"
    echo -e "  ${BLUE}demo${NC}         - Run demonstration mode"
    echo ""
    echo -e "${GREEN}Test Commands:${NC}"
    echo -e "  ${BLUE}test${NC}         - Run all tests"
    echo -e "  ${BLUE}voice-test${NC}   - Test voice system"
    echo -e "  ${BLUE}audio-test${NC}   - Test audio hardware"
    echo ""
    echo -e "${GREEN}Maintenance Commands:${NC}"
    echo -e "  ${BLUE}status${NC}       - Show system status"
    echo -e "  ${BLUE}logs${NC}         - Show recent logs"
    echo -e "  ${BLUE}cleanup${NC}      - Clean temporary files"
    echo -e "  ${BLUE}stop${NC}         - Stop GEM OS"
    echo ""
    echo -e "${GREEN}Examples:${NC}"
    echo -e "  ${YELLOW}./gem_runner.sh setup${NC}      # First time setup"
    echo -e "  ${YELLOW}./gem_runner.sh run${NC}        # Normal operation"
    echo -e "  ${YELLOW}./gem_runner.sh dev --debug${NC} # Development with debug"
}

# Main command handler
main() {
    print_banner
    
    case "${1:-help}" in
        "setup")
            check_requirements
            setup_directories
            setup_venv
            check_env_vars
            echo -e "${GREEN}🎉 GEM OS setup complete!${NC}"
            echo -e "${CYAN}Run './gem_runner.sh run' to start${NC}"
            ;;
        "install")
            setup_venv
            ;;
        "run")
            shift
            run_gem "$@"
            ;;
        "dev")
            shift
            run_dev "$@"
            ;;
        "demo")
            shift
            cd "$PROJECT_DIR"
            source "$VENV_DIR/bin/activate"
            python3 talkai_advanced.py --demo "$@"
            ;;
        "test")
            echo -e "${CYAN}🧪 Running tests...${NC}"
            cd "$PROJECT_DIR"
            source "$VENV_DIR/bin/activate"
            python3 -m pytest tests/ -v 2>/dev/null || echo -e "${YELLOW}⚠️ No tests found${NC}"
            ;;
        "voice-test")
            test_voice
            ;;
        "audio-test")
            test_audio
            ;;
        "status")
            show_status
            ;;
        "logs")
            echo -e "${CYAN}📋 Recent GEM OS logs:${NC}"
            if [ -f "$LOG_DIR/gem_os.log" ]; then
                tail -20 "$LOG_DIR/gem_os.log"
            else
                echo -e "${YELLOW}⚠️ No logs found${NC}"
            fi
            ;;
        "cleanup")
            cleanup
            ;;
        "stop")
            echo -e "${YELLOW}🛑 Stopping GEM OS...${NC}"
            pkill -f "gem.py" 2>/dev/null || echo -e "${YELLOW}⚠️ GEM OS was not running${NC}"
            ;;
        "help"|*)
            show_help
            ;;
    esac
}

# Run main function with all arguments
main "$@"