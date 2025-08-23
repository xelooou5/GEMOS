#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
💎 GEM OS - Learning Tools
Educational features and adaptive learning for all ages, powered by a central data store.
"""

import asyncio
import json
import logging
import random
import re
from datetime import datetime
from enum import Enum, auto
from typing import Dict, Any, List, Optional

from dataclasses import dataclass, asdict, field


@dataclass
class LearningSession:
    """Learning session data."""
    id: Optional[int] = None
    topic: str = ""
    session_type: str = "lesson"  # lesson, quiz, practice, review
    duration_minutes: int = 0
    score: Optional[float] = None
    completed: bool = False
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    notes: str = ""


@dataclass
class QuizQuestion:
    """Quiz question data."""
    id: Optional[int] = None
    topic: str = ""
    question: str = ""
    options: List[str] = field(default_factory=list)
    correct_answer: str = ""
    difficulty: str = "medium"  # easy, medium, hard
    explanation: str = ""


@dataclass
class LearningProgress:
    """Learning progress tracking."""
    topic: str = ""
    level: int = 1
    experience_points: int = 0
    sessions_completed: int = 0
    average_score: float = 0.0
    last_session: str = ""
    strengths: List[str] = field(default_factory=list)
    areas_for_improvement: List[str] = field(default_factory=list)


# --- State Management ---

class LearningState(Enum):
    """Manages the current state of the learning module."""
    IDLE = auto()
    IN_QUIZ = auto()
    IN_LESSON = auto()


# --- Core Logic ---


class AdaptiveLearning:
    """Adaptive learning system that adjusts to user performance."""

    def __init__(self, storage, logger: logging.Logger):
        self.storage = storage
        self.logger = logger

    async def generate_personalized_lesson_plan(self, topic: str) -> Dict[str, Any]:
        """Generate personalized lesson plan based on progress."""
        progress_data = await self.storage.get_learning_progress(topic)

        if not progress_data:
            # New learner
            return {
                "level": "beginner",
                "recommended_duration": 15,
                "focus_areas": ["basics", "fundamentals"],
                "difficulty": "easy",
                "session_type": "lesson"
            }

        progress = LearningProgress(**progress_data)

        # Experienced learner
        focus_areas = progress.areas_for_improvement if progress.areas_for_improvement else ["review"]

        return {
            "level": f"level_{progress.level}",
            "recommended_duration": min(30, 10 + progress.level * 5),
            "focus_areas": focus_areas,
            "difficulty": self._get_appropriate_difficulty(progress),
            "session_type": self._recommend_session_type(progress)
        }

    def _get_appropriate_difficulty(self, progress: LearningProgress) -> str:
        """Get appropriate difficulty based on progress."""
        if progress.average_score >= 0.85:
            return "hard"
        elif progress.average_score >= 0.65:
            return "medium"
        else:
            return "easy"

    def _recommend_session_type(self, progress: LearningProgress) -> str:
        """Recommend session type based on progress."""
        days_since_last = 99
        if progress.last_session:
            try:
                last_session_date = datetime.fromisoformat(progress.last_session)
                days_since_last = (datetime.now() - last_session_date).days
            except ValueError:
                pass

        if days_since_last > 7:
            return "review"
        elif progress.sessions_completed > 0 and progress.sessions_completed % 5 == 0:
            return "quiz"
        else:
            return "lesson"


class InteractiveLearning:
    """Interactive learning sessions and quizzes."""

    def __init__(self, storage, adaptive_learning: AdaptiveLearning, gem_assistant, logger: logging.Logger):
        self.storage = storage
        self.adaptive_learning = adaptive_learning
        self.gem = gem_assistant
        self.logger = logger

        # Current session state
        self.state: LearningState = LearningState.IDLE
        self.current_session: Optional[LearningSession] = None
        self.current_quiz: List[QuizQuestion] = []
        self.current_question_index = 0
        self.quiz_scores: List[bool] = []

    async def initialize_content(self):
        """Initialize built-in learning content if database is empty."""
        # Add some basic quiz questions for common topics
        basic_questions = [
            QuizQuestion(topic="português", question="Qual é o plural de 'animal'?",
                         options=["animais", "animals", "animales", "animaes"], correct_answer="animais",
                         difficulty="easy", explanation="O plural de 'animal' é 'animais'."),
            QuizQuestion(topic="matemática", question="Quanto é 7 x 8?", options=["54", "56", "58", "64"],
                         correct_answer="56", difficulty="easy", explanation="7 multiplicado por 8 é igual a 56."),
            QuizQuestion(topic="conhecimentos gerais", question="Qual é a capital do Brasil?",
                         options=["São Paulo", "Rio de Janeiro", "Brasília", "Salvador"], correct_answer="Brasília",
                         difficulty="easy", explanation="Brasília é a capital federal do Brasil."),
            QuizQuestion(topic="saúde", question="Quantos litros de água um adulto deve beber por dia, em média?",
                         options=["1 litro", "2 litros", "3 litros", "4 litros"], correct_answer="2 litros",
                         difficulty="easy", explanation="É recomendado beber cerca de 2 litros de água por dia.")
        ]

        for question in basic_questions:
            existing = await self.storage.get_quiz_questions(question.topic, limit=1)
            if not existing:
                await self.storage.save_quiz_question(asdict(question))
                self.logger.info(f"Added built-in quiz question for topic: {question.topic}")

    async def start_learning_session(self, topic: str, session_type: str = "auto") -> str:
        """Start a learning session."""
        lesson_plan = await self.adaptive_learning.generate_personalized_lesson_plan(topic)

        if session_type == "auto":
            session_type = lesson_plan["session_type"]

        self.current_session = LearningSession(topic=topic, session_type=session_type)

        if session_type == "quiz":
            self.state = LearningState.IN_QUIZ
            return await self._start_quiz(topic, lesson_plan["difficulty"])
        else:  # lesson, review, or practice
            self.state = LearningState.IN_LESSON
            if session_type == "lesson":
                return await self._start_lesson(topic)
            else:
                return await self._start_review(topic)

    async def _start_quiz(self, topic: str, difficulty: str) -> str:
        """Start a quiz session."""
        questions_data = await self.storage.get_quiz_questions(topic, difficulty, 5)
        self.current_quiz = [QuizQuestion(**q) for q in questions_data]

        if not self.current_quiz:
            self.state = LearningState.IDLE
            return f"Não encontrei perguntas sobre {topic}. Que tal começar com uma lição básica?"

        self.current_question_index = 0
        self.quiz_scores = []

        return await self._ask_current_question()

    async def _ask_current_question(self) -> str:
        """Ask the current quiz question."""
        question = self.current_quiz[self.current_question_index]

        options_text = "\n".join(f"{i + 1}. {option}" for i, option in enumerate(question.options))
        return f"Pergunta {self.current_question_index + 1}: {question.question}\n\n{options_text}\n\nDiga o número ou a resposta correta."
    
    def _parse_user_answer(self, answer_text: str, options: List[str]) -> Optional[str]:
        """Parses the user's spoken answer to find the chosen option."""
        answer_text = answer_text.lower().strip()

        # Check for number words ("um", "dois", etc.)
        number_words = {"um": 1, "uma": 1, "dois": 2, "duas": 2, "três": 3, "quatro": 4, "cinco": 5}
        for word, number in number_words.items():
            if word in answer_text:
                if 1 <= number <= len(options):
                    return options[number - 1]

        # Check for digits
        match = re.search(r'\d+', answer_text)
        if match:
            number = int(match.group(0))
            if 1 <= number <= len(options):
                return options[number - 1]

        # Check for direct match of an option
        for opt in options:
            if opt.lower() in answer_text:
                return opt

        return None # Could not parse

    async def answer_quiz_question(self, answer: str) -> str:
        """Process quiz answer."""
        if self.state != LearningState.IN_QUIZ:
            return "Não estamos em um quiz no momento. Diga 'iniciar quiz sobre [tópico]' para começar."

        question = self.current_quiz[self.current_question_index]
        parsed_answer = self._parse_user_answer(answer, question.options)

        if parsed_answer is None:
            return "Não entendi sua resposta. Por favor, diga o número ou a opção desejada."

        is_correct = parsed_answer.lower() == question.correct_answer.lower()
        self.quiz_scores.append(is_correct)

        response = "Correto! " if is_correct else f"Incorreto. A resposta correta é: {question.correct_answer}. "
        if question.explanation:
            response += question.explanation + " "

        self.current_question_index += 1

        if self.current_question_index < len(self.current_quiz):
            response += "\n\nPróxima pergunta: " + await self._ask_current_question()
        else:
            response += "\n\n" + await self._finish_quiz()

        return response

    async def _finish_quiz(self) -> str:
        """Finish quiz and calculate score."""
        if not self.quiz_scores:
            self._reset_state()
            return "Quiz finalizado sem respostas."

        correct_answers = sum(self.quiz_scores)
        total_questions = len(self.quiz_scores)
        score = correct_answers / total_questions if total_questions > 0 else 0.0

        if self.current_session:
            self.current_session.score = score
            self.current_session.completed = True
            await self.storage.save_learning_session(asdict(self.current_session))
            await self._update_learning_progress(self.current_session.topic, score)

        percentage = int(score * 100)
        feedback = "Excelente trabalho!" if percentage >= 80 else "Bom trabalho!" if percentage >= 60 else "Continue praticando!"

        result = f"Quiz finalizado! Você acertou {correct_answers} de {total_questions} perguntas ({percentage}%). {feedback}"

        self._reset_state()
        return result
    
    async def _start_lesson(self, topic: str) -> str:
        """Start a lesson session."""
        lesson_content = await self._generate_lesson_content(topic)
        if self.current_session:
            self.current_session.completed = True
            await self.storage.save_learning_session(asdict(self.current_session))
        self._reset_state()
        return lesson_content

    async def _generate_lesson_content(self, topic: str) -> str:
        """Generate lesson content for topic using the LLM."""
        if self.gem.llm_handler:
            prompt = f"Crie uma lição educativa sobre {topic} de forma simples e acessível para um assistente de voz. Seja conciso e claro."
            response = await self.gem.llm_handler.generate_response(prompt)
            return response.get("content", f"Vamos aprender sobre {topic}.")
        return f"Vamos aprender sobre {topic}. Que aspecto específico você gostaria de conhecer?"

    async def _start_review(self, topic: str) -> str:
        """Start a review session."""
        progress_data = await self.storage.get_learning_progress(topic)
        areas = ", ".join(progress_data.get('areas_for_improvement', [])) if progress_data else ""
        content = f"Vamos revisar {topic}" + (f", focando em: {areas}." if areas else ".")

        if self.gem.llm_handler:
            prompt = f"Crie um resumo de revisão sobre {topic} para um assistente de voz, destacando os pontos mais importantes de forma clara e concisa."
            review_content = await self.gem.llm_handler.generate_response(prompt)
            content += "\n\n" + review_content.get("content", "")

        if self.current_session:
            self.current_session.completed = True
            await self.storage.save_learning_session(asdict(self.current_session))

        self._reset_state()
        return content

    async def _update_learning_progress(self, topic: str, score: float):
        """Update learning progress after a session."""
        progress_data = await self.storage.get_learning_progress(topic)
        progress = LearningProgress(**progress_data) if progress_data else LearningProgress(topic=topic)

        progress.sessions_completed += 1
        progress.experience_points += int(score * 100)
        progress.last_session = datetime.now().isoformat()

        # Weighted average to give more importance to recent scores
        total_sessions = progress.sessions_completed
        if total_sessions > 1:
            progress.average_score = ((progress.average_score * (total_sessions - 1)) + score) / total_sessions
        else:
            progress.average_score = score

        progress.level = min(10, 1 + progress.experience_points // 500)

        await self.storage.save_learning_progress(asdict(progress))
        self.logger.info(f"Updated learning progress for '{topic}': Level {progress.level}, Score {progress.average_score:.2f}")

    def _reset_state(self):
        """Resets the interactive session state."""
        self.state = LearningState.IDLE
        self.current_session = None
        self.current_quiz = []
        self.current_question_index = 0
        self.quiz_scores = []
        self.logger.info("Learning session state has been reset.")


# --- Main Manager Class ---

class LearningTools:
    """Main learning tools manager."""

    def __init__(self, gem_assistant, logger: Optional[logging.Logger] = None):
        self.gem = gem_assistant
        self.logger = logger or logging.getLogger("LearningTools")

        if not hasattr(self.gem, 'storage') or not self.gem.storage:
            raise ValueError("Storage module is not available in GEM instance.")

        self.adaptive_learning = AdaptiveLearning(self.gem.storage, self.logger)
        self.interactive_learning = InteractiveLearning(
            self.gem.storage, self.adaptive_learning, self.gem, self.logger
        )

    async def initialize(self):
        """Initialize learning tools and built-in content."""
        self.logger.info("Initializing learning tools...")
        await self.interactive_learning.initialize_content()
        self.logger.info("Learning tools initialized")

    async def teach_topic(self, topic: str) -> str:
        """Teach about a specific topic."""
        return await self.interactive_learning.start_learning_session(topic, "lesson")

    async def start_quiz(self, topic: str) -> str:
        """Start a quiz on a topic."""
        return await self.interactive_learning.start_learning_session(topic, "quiz")

    async def answer_question(self, answer: str) -> str:
        """Answer current quiz question."""
        if self.interactive_learning.state != LearningState.IN_QUIZ:
            return "Não estamos em um quiz no momento. Diga 'iniciar quiz sobre [tópico]' para começar."
        return await self.interactive_learning.answer_quiz_question(answer)

    async def get_learning_progress(self, topic: str) -> str:
        """Get learning progress for a topic."""
        progress_data = await self.gem.storage.get_learning_progress(topic)
        if not progress_data:
            return f"Nenhum progresso registrado para {topic}. Que tal começar uma lição?"

        progress = LearningProgress(**progress_data)
        status = (
            f"Progresso em {topic}:\n"
            f"- Nível: {progress.level}\n"
            f"- Pontos de Experiência: {progress.experience_points}\n"
            f"- Sessões Concluídas: {progress.sessions_completed}\n"
            f"- Pontuação Média: {progress.average_score:.0%}"
        )
        return status

    async def suggest_learning_activity(self) -> str:
        """Suggest a learning activity."""
        # A more advanced version could check recent topics from history
        topics = ["português", "matemática", "conhecimentos gerais", "saúde", "tecnologia"]
        suggested_topic = random.choice(topics)

        lesson_plan = await self.adaptive_learning.generate_personalized_lesson_plan(suggested_topic)

        return (
            f"Que tal aprender sobre {suggested_topic}? "
            f"Com base no seu progresso, recomendo uma sessão de {lesson_plan['session_type']} "
            f"com duração de aproximadamente {lesson_plan['recommended_duration']} minutos."
        )