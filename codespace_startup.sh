#!/bin/bash
# Codespace Startup Script - Auto-enable Copilot background work

# Install Copilot CLI if not present
if ! command -v gh &> /dev/null; then
    curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
    sudo apt update
    sudo apt install gh -y
fi

# Enable Copilot
gh extension install github/gh-copilot || true

# Install dependencies
pip install -r requirements.txt

# Start Copilot daemon
chmod +x copilot_daemon.sh
nohup ./copilot_daemon.sh > copilot_output.log 2>&1 &

echo "🤖 Copilot Background System started in Codespace"
echo "🤖 Copilot is now working continuously on GEM OS"
