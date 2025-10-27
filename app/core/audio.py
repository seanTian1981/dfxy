from __future__ import annotations

import queue
import threading
from dataclasses import dataclass
from typing import Optional

try:
    import pyttsx3  # type: ignore
except ImportError:  # pragma: no cover - graceful fallback if dependency missing
    pyttsx3 = None


@dataclass
class SpeechTask:
    utterance: str
    wait: bool = False


class TextToSpeech:
    """Thin wrapper around pyttsx3 with thread-safe queue."""

    def __init__(self) -> None:
        self._engine = pyttsx3.init() if pyttsx3 is not None else None
        self._queue: "queue.Queue[SpeechTask]" = queue.Queue()
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        if self._engine is not None:
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()

    def speak(self, utterance: str, wait: bool = False) -> None:
        if not utterance:
            return
        if self._engine is None:
            # Fallback: simply print to console for environments without audio support.
            print(f"[TTS模拟] {utterance}")
            return
        self._queue.put(SpeechTask(utterance=utterance, wait=wait))

    def shutdown(self) -> None:
        if self._engine is None:
            return
        self._stop_event.set()
        self._queue.put(SpeechTask("", wait=False))
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1)
        self._engine.stop()

    def _run(self) -> None:
        assert self._engine is not None
        while not self._stop_event.is_set():
            try:
                task = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue
            if not task.utterance:
                continue
            self._engine.say(task.utterance)
            self._engine.runAndWait()
            self._queue.task_done()
            if task.wait:
                self._queue.join()
