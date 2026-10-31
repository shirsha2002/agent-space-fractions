"""Core game logic for Space Fractions.

This module is headless and independent of the GUI. It defines Question and Game
classes with a stable public API.
"""
from fractions import Fraction
from typing import List, Optional

class Question:
    """A single multiple-choice fraction question."""
    def __init__(self, qid: str, prompt: str, options: List[str], answer: str, explanation: str = ''):
        """
        Initialize a question.
        qid: unique identifier
        prompt: question text
        options: list of answer choices as strings
        answer: correct choice text
        explanation: optional explanation shown after answering
        """
        if not qid or not isinstance(qid, str):
            raise ValueError("qid must be a non-empty string")
        if not prompt or not isinstance(prompt, str):
            raise ValueError("prompt must be a non-empty string")
        if not isinstance(options, (list, tuple)) or len(options) < 2:
            raise ValueError("options must be a list with at least two choices")
        if answer not in options:
            raise ValueError("answer must be one of the options")
        self.qid = qid
        self.prompt = prompt
        self.options = list(options)
        self.answer = answer
        self.explanation = explanation

    def check(self, answer_string: str) -> bool:
        """Return True if answer_string is equivalent to the correct answer.
        Fractions are compared using fractions.Fraction, so '1/2' matches '2/4'.
        Invalid inputs return False.
        """
        if not isinstance(answer_string, str):
            return False
        try:
            correct = Fraction(self.answer)
            attempt = Fraction(answer_string)
            return correct == attempt
        except (ValueError, ZeroDivisionError):
            return False

class Game:
    """Manages game state for a sequence of questions."""
    def __init__(self, questions: List[Question]):
        """Initialize a game with a non-empty list of questions."""
        if not questions or not isinstance(questions, (list, tuple)):
            raise ValueError("questions must be a non-empty list")
        self.questions = list(questions)
        self.state = 'playing'
        self.score = 0
        self.index = 0
        self.answered_current = False

    def current_question(self) -> Optional[Question]:
        """Return the current question, or None if game over."""
        if self.state == 'game_over' or self.index >= len(self.questions):
            return None
        return self.questions[self.index]

    def submit(self, answer_string: str) -> bool:
        """Submit an answer for the current question.
        Returns True if correct, False otherwise.
        Raises ValueError if game is paused, over, or current question already answered.
        """
        if self.state == 'paused':
            raise ValueError("Cannot submit while paused")
        if self.state == 'game_over':
            raise ValueError("Cannot submit after game over")
        if self.answered_current:
            raise ValueError("Current question already answered")
        question = self.questions[self.index]
        correct = question.check(answer_string)
        if correct:
            self.score += 1
        self.answered_current = True
        return correct

    def next_question(self) -> None:
        """Advance to next question. Raises ValueError if current question unanswered or game not playing."""
        if self.state == 'paused':
            raise ValueError("Cannot advance while paused")
        if self.state == 'game_over':
            raise ValueError("Cannot advance after game over")
        if not self.answered_current:
            raise ValueError("Current question not answered")
        self.index += 1
        self.answered_current = False
        if self.index >= len(self.questions):
            self.state = 'game_over'

    def pause(self) -> None:
        """Pause the game. Raises ValueError if not currently playing."""
        if self.state != 'playing':
            raise ValueError("Can only pause when playing")
        self.state = 'paused'

    def resume(self) -> None:
        """Resume the game. Raises ValueError if not currently paused."""
        if self.state != 'paused':
            raise ValueError("Can only resume when paused")
        self.state = 'playing'

    def restart(self) -> None:
        """Reset game to initial state."""
        self.state = 'playing'
        self.score = 0
        self.index = 0
        self.answered_current = False
