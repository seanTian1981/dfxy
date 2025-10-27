from __future__ import annotations

import math
import time
from dataclasses import dataclass, field


@dataclass
class PracticeStats:
    correct_letters: int = 0
    total_letters: int = 0
    correct_words: int = 0
    start_time: float = field(default_factory=time.monotonic)

    def reset(self) -> None:
        self.correct_letters = 0
        self.total_letters = 0
        self.correct_words = 0
        self.start_time = time.monotonic()

    def register_word(self, word_length: int) -> None:
        self.correct_words += 1
        self.correct_letters += word_length
        self.total_letters += word_length

    def register_error(self, added_letters: int = 1) -> None:
        self.total_letters += max(added_letters, 0)

    @property
    def accuracy(self) -> float:
        if self.total_letters == 0:
            return 1.0
        return self.correct_letters / self.total_letters

    @property
    def elapsed_minutes(self) -> float:
        return max((time.monotonic() - self.start_time) / 60.0, 1e-6)

    @property
    def words_per_minute(self) -> float:
        return self.correct_words / self.elapsed_minutes

    def format_accuracy(self) -> str:
        return f"{self.accuracy * 100:.1f}%"

    def format_speed(self) -> str:
        return f"{self.words_per_minute:.1f} 词/分钟"


@dataclass
class EssayStats(PracticeStats):
    def register_completion(self, essay_length: int) -> None:
        self.correct_letters = essay_length
        self.total_letters = essay_length
        self.correct_words = essay_length // 5  # rough approximation for display

    @property
    def words_per_minute(self) -> float:
        # interpret characters per minute into approximate words
        return self.correct_letters / 5.0 / self.elapsed_minutes

    def format_speed(self) -> str:
        return f"{self.words_per_minute:.1f} 词/分钟"
