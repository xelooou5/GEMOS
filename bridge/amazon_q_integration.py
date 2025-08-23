#!/usr/bin/env python3
"""
Amazon Q Integration - For Amazon Q to log messages
"""

from ai_bridge import AIBridge

bridge = AIBridge()

def log_amazon_q_message(content):
    """Log message from Amazon Q"""
    bridge.log_message('amazon_q', content)
    
def get_context():
    """Get all AI messages and context"""
    return bridge.get_messages()

def update_gem_context(gem_status):
    """Update GEM OS context for other AIs"""
    bridge.update_context({
        "gem_status": gem_status,
        "timestamp": bridge._read_json(bridge.files['current_context'])
    })

# Log this integration
log_amazon_q_message({
    "type": "system",
    "content": "Amazon Q integration active - Enhanced AI bridge implemented",
    "capabilities": ["message logging", "context sharing", "GEM OS integration"]
})