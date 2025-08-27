#!/usr/bin/env python3
"""
GEM OS - Slack Socket Mode Integration
Replaces HTTP endpoints with WebSocket connection
"""

import asyncio
import json
import logging
import os
from dotenv import load_dotenv
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler

# Load environment variables
load_dotenv()

# Initialize Slack app
app = AsyncApp(token=os.getenv('SLACK_BOT_TOKEN'))

@app.event("app_mention")
async def handle_mention(event, say):
    """Handle app mentions for accessibility assistance"""
    user = event.get("user")
    text = event.get("text", "")
    await say(f"GEM OS accessibility assistant ready to help <@{user}>!")
    logging.info(f"GEM mentioned by {user}: {text}")

@app.event("message")
async def handle_message(event, say):
    """Handle messages for voice commands"""
    if event.get("channel_type") == "im":  # Direct messages
        text = event.get("text", "")
        user = event.get("user")
        logging.info(f"DM from {user}: {text}")

@app.event("reaction_added")
async def handle_reaction(event):
    """Handle reactions for accessibility feedback"""
    reaction = event.get("reaction")
    user = event.get("user")
    logging.info(f"Reaction {reaction} from {user}")

@app.event("file_shared")
async def handle_file(event):
    """Handle file sharing for alt-text generation"""
    file_id = event.get("file_id")
    user = event.get("user_id")
    logging.info(f"File {file_id} shared by {user}")

async def main():
    """Start Socket Mode handler"""
    handler = AsyncSocketModeHandler(app, os.getenv('SLACK_APP_TOKEN'))
    await handler.start_async()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())