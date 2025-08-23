#!/bin/bash
# Quick setup for enhanced development

echo "🚀 GEM OS Quick Enhanced Setup"

# Copy environment template
if [ ! -f .env ]; then
    cp .env.template .env
    echo "✅ Created .env file - please fill in your API keys"
fi

# Install enhanced requirements
pip install -r requirements.txt

# Setup pre-commit hooks
pre-commit install

# Create initial commit
if [ ! -f .git/refs/heads/main ]; then
    git add .
    git commit -m "Initial GEM OS Enhanced setup"
fi

echo "✅ Quick setup complete!"
echo "Next steps:"
echo "1. Fill in your API keys in .env file"
echo "2. Run: ./scripts/setup_api_keys.sh (for API key links)"
echo "3. Run: python scripts/dev_enhanced.py"
