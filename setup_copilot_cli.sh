#!/bin/bash
# GitHub Copilot CLI Setup for GEMOS

echo "🤖 Setting up GitHub Copilot CLI..."

# Install GitHub CLI if not present
if ! command -v gh &> /dev/null; then
    echo "Installing GitHub CLI..."
    curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
    sudo apt update
    sudo apt install gh -y
fi

# Install Copilot CLI extension
echo "Installing Copilot CLI extension..."
gh extension install github/gh-copilot

# Setup ghcs alias for command execution
echo "Setting up ghcs alias..."
echo 'alias ghcs="gh copilot suggest"' >> ~/.bashrc
echo 'alias ghce="gh copilot explain"' >> ~/.bashrc

# Source the aliases
source ~/.bashrc

echo "✅ GitHub Copilot CLI setup complete!"
echo "✅ Use 'gh copilot suggest' for command suggestions"
echo "✅ Use 'gh copilot explain' for command explanations"
echo "✅ Use 'ghcs' and 'ghce' as shortcuts"
