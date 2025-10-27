from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from app.core.audio import TextToSpeech
from app.ui.essay_practice import EssayPracticeFrame
from app.ui.pk_mode import PkModeFrame
from app.ui.word_practice import WordPracticeFrame


class MainApplication(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("英语四六级打字练习系统")
        self.geometry("960x720")
        self.minsize(800, 600)

        self.tts = TextToSpeech()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self._build_ui()

    def _build_ui(self) -> None:
        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True)

        word_practice = WordPracticeFrame(notebook, tts=self.tts)
        essay_practice = EssayPracticeFrame(notebook)
        pk_mode = PkModeFrame(notebook)

        notebook.add(word_practice, text="单词打字练习")
        notebook.add(essay_practice, text="优秀作文练习")
        notebook.add(pk_mode, text="PK 对战")

    def on_close(self) -> None:
        self.tts.shutdown()
        self.destroy()


def run() -> None:
    app = MainApplication()
    app.mainloop()
