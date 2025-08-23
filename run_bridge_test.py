#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
💎 GEM OS - AI Bridge Test Runner
Initializes and tests the AI collaboration bridge.
"""

from bridge.ai_bridge import EnhancedAIBridge
from bridge.ai_agents import GeminiAgent, CopilotAgent, AmazonQAgent
import time

def main():
    """Initializes the bridge and simulates a conversation."""
    print("--- 🚀 Initializing Enhanced AI Collaboration Bridge ---")
    bridge = EnhancedAIBridge()
    time.sleep(1) # Allow for file creation

    print("\n--- 🤖 Activating AI Agents ---")
    gemini = GeminiAgent(bridge)
    copilot = CopilotAgent(bridge)
    amazon_q = AmazonQAgent(bridge)
    time.sleep(1)

    print("\n--- 💬 Simulating a Collaborative Session ---")
    copilot_message_content = "Testing AI bridge connection. Awaiting response from Gemini and Amazon Q."
    copilot.send_message(copilot_message_content)
    print(f"\n[Copilot] Sent: '{copilot_message_content}'")
    time.sleep(1)

    # Gemini's turn to respond
    print("\n--- ♊ Gemini's Turn ---")
    gemini_log = gemini.review_shared_log(last_n=5)
    copilot_message = next((msg for msg in reversed(gemini_log) if msg['sender'] == 'copilot'), None)
    if copilot_message:
        gemini.acknowledge(copilot_message)
        gemini.send_message("Gemini acknowledges. Bridge connection is operational. Ready to architect solutions.")
    else:
        print("[Gemini] Did not find Copilot's message.")
    time.sleep(1)

    # Amazon Q's turn to respond
    print("\n--- 🇶 Amazon Q's Turn ---")
    q_log = amazon_q.review_shared_log(last_n=5)
    copilot_message_for_q = next((msg for msg in reversed(q_log) if msg['sender'] == 'copilot'), None)
    if copilot_message_for_q:
        amazon_q.acknowledge(copilot_message_for_q)
        amazon_q.send_message("Amazon Q acknowledges. Connection confirmed. Standing by to assist with cloud integration and DevOps.")
    else:
        print("[Amazon Q] Did not find Copilot's message.")
    time.sleep(1)

    print("\n--- 📜 Final Shared Log Review ---")
    shared_messages = bridge.get_messages(channel_name='shared', last_n=10)

    if not shared_messages:
        print("No messages found in the shared log.")
    else:
        for msg in shared_messages:
            print(f"[{msg['timestamp']}] {msg['sender'].title()}: {msg['content']}")

    print("\n--- ✅ AI Bridge Test Complete ---")
    print(f"Logs and channels are available in: {bridge.base_dir}")

if __name__ == "__main__":
    main()