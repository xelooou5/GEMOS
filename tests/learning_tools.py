#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ðŸ’Ž GEM OS - Learning Tools (features/learning_tools.py)
Claude-style structure + Gemini-style simplicity + my extra improvements.

Responsibilities
----------------
- Provide educational tools powered by LLM + TTS
- Quiz generation, summarization, concept explanation
- Flashcards and study sessions
"""

from __future__ import annotations

import asyncio
from typing import List, Dict, Any


class LearningTools:
    def __init__(self, config_manager, llm_handler=None, tts_module=None):
        self.config = config_manager
        self.llm = llm_handler
        self.tts = tts_module
        self.usage_counts = {
            "quiz": 0,
            "summary": 0,
            "explanation": 0,
            "flashcards": 0,
            "study_sessions": 0,
        }

    # ------------------------------------------------------------------- Tools

    async def generate_quiz(self, topic: str, num_questions: int = 5) -> List[Dict[str, str]]:
        """Generate a quiz about a topic."""
        self.usage_counts["quiz"] += 1
        if not self.llm:
            return [{"q": f"What is {topic}?", "a": f"{topic} is important."}]

        prompt = f"Create {num_questions} quiz questions with answers about {topic}."
        resp = await self.llm.process_query(prompt)
        questions = [{"q": line.split("?")[0] + "?", "a": "Answer TBD"} for line in resp.split("\n") if "?" in line]
        return questions

    async def summarize_text(self, text: str) -> str:
        """Summarize text into bullet points."""
        self.usage_counts["summary"] += 1
        if not self.llm:
            return text[:100] + "..."
        prompt = f"Summarize the following text in bullet points:\n{text}"
        resp = await self.llm.process_query(prompt)
        if self.tts:
            await self.tts.speak("Here is a summary of the text.")
        return resp

    async def explain_concept(self, concept: str) -> str:
        """Explain a concept in simple terms."""
        self.usage_counts["explanation"] += 1
        if not self.llm:
            return f"{concept} is something important."
        prompt = f"Explain {concept} in simple terms for a beginner."
        resp = await self.llm.process_query(prompt)
        if self.tts:
            await self.tts.speak(f"Explanation of {concept}: {resp}")
        return resp

    async def flashcards(self, topic: str, num_cards: int = 5) -> List[Dict[str, str]]:
        """Generate flashcards for a topic."""
        self.usage_counts["flashcards"] += 1
        if not self.llm:
            return [{"front": f"What is {topic}?", "back": f"{topic} is important."}]
        prompt = f"Generate {num_cards} flashcards for learning about {topic}."
        resp = await self.llm.process_query(prompt)
        cards = [{"front": line, "back": "Answer TBD"} for line in resp.split("\n") if line.strip()]
        return cards

    async def study_session(self, topic: str, minutes: int = 10) -> str:
        """Generate a study plan for a topic."""
        self.usage_counts["study_sessions"] += 1
        if not self.llm:
            return f"Study {topic} for {minutes} minutes."
        prompt = f"Create a {minutes}-minute study session plan for {topic}."
        resp = await self.llm.process_query(prompt)
        if self.tts:
            await self.tts.speak(f"Starting a study session about {topic}.")
        return resp

    # ------------------------------------------------------------------- Utils

    def get_usage_stats(self) -> dict:
        return dict(self.usage_counts)

    def shutdown(self) -> None:
        """Optional cleanup hook."""
        pass


# =============================================================================
# CLI Test
# =============================================================================

if __name__ == "__main__":
    import asyncio
    from core.config_manager import ConfigManager
    from core.llm_handler import LLMHandler
    from core.tts_module import TTSModule

    cfg = ConfigManager()
    cfg.load()
    llm = LLMHandler(cfg)
    tts = TTSModule(cfg)
    learn = LearningTools(cfg, llm, tts)

    async def _test():
        q = await learn.generate_quiz("Python programming", 3)
        print("Quiz:", q)
        s = await learn.summarize_text("Python is a programming language...")
        print("Summary:", s)
        e = await learn.explain_concept("Artificial Intelligence")
        print("Explanation:", e)
        f = await learn.flashcards("Databases", 3)
        print("Flashcards:", f)
        plan = await learn.study_session("Machine Learning", 5)
        print("Study session:", plan)
        print("Usage stats:", learn.get_usage_stats())

    asyncio.run(_test())
