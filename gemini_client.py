#!/usr/bin/env python3
"""
💎 GEM OS - Gemini Pro Client
Handles all communication with the Google Generative AI API.
English first, Portuguese (pt-BR) second.
"""
import os
import google.generativeai as genai
import re

class GeminiProClient:
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_AI_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_AI_API_KEY environment variable not set.")
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-pro')
        self.reset_chat()

    def generate_response(self, prompt: str):
        """Sends a prompt to Gemini Pro and yields complete sentences as they arrive."""
        try:
            print("🧠 Gemini is thinking...")
            response = self.chat.send_message(prompt, stream=True)
            buffer = ""
            for chunk in response:
                print(chunk.text, end="", flush=True)
                buffer += chunk.text
                # Split the buffer into sentences, keeping the delimiter.
                sentences = re.split(r'(?<=[.?!])\s*', buffer)
                
                # The last part of the split is an incomplete sentence, so we keep it in the buffer.
                if len(sentences) > 1:
                    for sentence in sentences[:-1]:
                        if sentence.strip():
                            yield sentence.strip()
                    buffer = sentences[-1]
        
            # Yield any remaining text in the buffer after the loop finishes.
            if buffer.strip():
                yield buffer.strip()
            print()  # Newline after streaming is complete
        except Exception as e:
            print(f"❌ Error communicating with Gemini Pro: {e}")
            yield "I'm sorry, I encountered an error while trying to think."

    def reset_chat(self):
        """Clears the conversation history to start fresh."""
        # Clears the chat history by starting a new chat instance with the initial system prompt.
        # Limpa o histórico da conversa iniciando uma nova instância de chat com o prompt inicial do sistema.
        self.chat = self.model.start_chat(history=[
            {
                "role": "user", "parts": [
                    "You are Gemini, a friendly and professional AI assistant built into the GEM OS. "
                    "Provide clear, concise, and helpful answers. You are a world-class expert."
                ]
            },
            {"role": "model", "parts": ["Understood. I am Gemini, ready to assist."]}
        ])
        print("🧠 Gemini chat history has been reset.")