#!/bin/bash
# GEMOS Command Explanation Helper

if [ $# -eq 0 ]; then
    echo "Usage: ./gemos_explain.sh <command>"
    echo "Example: ./gemos_explain.sh 'pip install -r requirements.txt'"
    exit 1
fi

echo "🤖 Explaining command: $*"
gh copilot explain "$*"
