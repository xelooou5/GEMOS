# GitHub Copilot CLI Usage for GEMOS

## Setup
Run the setup script:
```bash
./setup_copilot_cli.sh
```

## Basic Usage

### Get Command Suggestions
```bash
gh copilot suggest "Install Python dependencies"
gh copilot suggest "Fix security vulnerabilities"
gh copilot suggest "Implement voice recognition"
```

### Explain Commands
```bash
gh copilot explain "pip install -r requirements.txt"
gh copilot explain "python -m pytest tests/"
```

### Quick Shortcuts
```bash
ghcs "Deploy voice assistant"  # Suggest commands
ghce "docker run -p 8080:80"  # Explain commands
```

## GEMOS Helpers

### Development Assistant
```bash
./gemos_dev_help.sh
```

### Command Explanation
```bash
./gemos_explain.sh "complex command here"
```

### Quick Tasks
```bash
./gemos_quick_tasks.sh
```

## Integration with Team Workflow

1. **Copilot suggests commands** for development tasks
2. **Team members get explanations** for complex commands
3. **Automated suggestions** through GitHub workflows
4. **Real-time CLI assistance** during development

## Examples for GEMOS Development

```bash
# Voice system development
gh copilot suggest "Implement speech recognition with faster-whisper"

# Security fixes
gh copilot suggest "Fix Python security vulnerabilities"

# Accessibility
gh copilot suggest "Add screen reader support to Python app"

# Deployment
gh copilot suggest "Deploy Python voice assistant to cloud"
```
