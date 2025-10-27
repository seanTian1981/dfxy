from __future__ import annotations

import random
import tkinter as tk
from tkinter import messagebox, ttk
from typing import List

from app.core.audio import TextToSpeech
from app.core.data_loader import WordEntry, load_words
from app.core.stats import PracticeStats


class WordPracticeFrame(ttk.Frame):
    def __init__(self, master: tk.Misc, tts: TextToSpeech) -> None:
        super().__init__(master)
        self.tts = tts
        self.current_level = tk.StringVar(value="cet4")
        self.current_word: WordEntry | None = None
        self.letter_labels: List[tk.Label] = []
        self.stats = PracticeStats()
        self.entry_var = tk.StringVar()
        self.status_var = tk.StringVar(value="速度: 0.0 词/分钟 | 正确率: 100.0%")
        self.word_bank: dict[str, List[WordEntry]] = {
            "cet4": load_words("cet4"),
            "cet6": load_words("cet6"),
        }
        self.word_queue: List[WordEntry] = []

        self._build_ui()
        self._reset_queue()
        self._next_word()

    def _build_ui(self) -> None:
        control_frame = ttk.Frame(self)
        control_frame.pack(fill=tk.X, padx=12, pady=8)

        ttk.Label(control_frame, text="选择词汇等级:").pack(side=tk.LEFT)
        level_combobox = ttk.Combobox(
            control_frame,
            values=("cet4", "cet6"),
            state="readonly",
            textvariable=self.current_level,
            width=8,
        )
        level_combobox.bind("<<ComboboxSelected>>", self._on_level_change)
        level_combobox.pack(side=tk.LEFT, padx=(8, 16))

        ttk.Button(control_frame, text="重置练习", command=self._restart_practice).pack(side=tk.LEFT)
        ttk.Button(control_frame, text="播放发音", command=self._speak_current_word).pack(side=tk.LEFT, padx=(8, 0))

        display_frame = ttk.Frame(self)
        display_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        self.title_label = ttk.Label(display_frame, text="", font=("Helvetica", 32, "bold"))
        self.title_label.pack(pady=(0, 12))

        self.phonetic_label = ttk.Label(display_frame, text="", font=("Helvetica", 16))
        self.phonetic_label.pack()

        self.meaning_label = ttk.Label(display_frame, text="", wraplength=600, justify=tk.LEFT)
        self.meaning_label.pack(pady=(12, 4))

        self.example_label = ttk.Label(display_frame, text="", wraplength=600, justify=tk.LEFT)
        self.example_label.pack()

        letters_frame = ttk.Frame(display_frame)
        letters_frame.pack(pady=(20, 10))
        self.letters_container = letters_frame

        entry = ttk.Entry(display_frame, textvariable=self.entry_var, font=("Helvetica", 20))
        entry.pack(pady=(10, 6), fill=tk.X)
        entry.bind("<KeyRelease>", self._on_input_change)
        entry.focus_set()

        self.status_bar = ttk.Label(self, textvariable=self.status_var, anchor=tk.W)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM, padx=12, pady=4)

    def _reset_queue(self) -> None:
        level = self.current_level.get()
        base_list = self.word_bank[level][:]
        random.shuffle(base_list)
        self.word_queue = base_list
        self.stats.reset()
        self._update_status()

    def _on_level_change(self, _event: tk.Event | None = None) -> None:
        self._restart_practice()

    def _restart_practice(self) -> None:
        self._reset_queue()
        self._next_word()

    def _speak_current_word(self) -> None:
        if self.current_word is None:
            return
        utterance = f"{self.current_word.word}. {self.current_word.meaning}"
        self.tts.speak(utterance)

    def _next_word(self) -> None:
        if not self.word_queue:
            messagebox.showinfo("练习完成", "该等级的全部单词已练习完毕。即将重新开始。")
            self._reset_queue()
        self.current_word = self.word_queue.pop()
        self.entry_var.set("")
        self._render_current_word()
        self._speak_current_word()

    def _render_current_word(self) -> None:
        assert self.current_word is not None
        word = self.current_word.word
        for label in self.letter_labels:
            label.destroy()
        self.letter_labels.clear()

        for char in word:
            lbl = tk.Label(
                self.letters_container,
                text=char,
                font=("Helvetica", 28, "bold"),
                padx=6,
                pady=4,
            )
            lbl.pack(side=tk.LEFT)
            self.letter_labels.append(lbl)

        self.title_label.config(text=self.current_word.word)
        self.phonetic_label.config(text=self.current_word.phonetic)
        self.meaning_label.config(text=f"释义：{self.current_word.meaning}")
        self.example_label.config(text=f"例句：{self.current_word.example}")

        for label in self.letter_labels:
            label.config(fg="#1e1e1e")

    def _on_input_change(self, _event: tk.Event | None = None) -> None:
        if self.current_word is None:
            return
        typed = self.entry_var.get()
        target = self.current_word.word
        lowercase_target = target.lower()

        if not typed:
            for label in self.letter_labels:
                label.config(fg="#1e1e1e")
            return

        for idx, label in enumerate(self.letter_labels):
            if idx < len(typed):
                if typed[idx].lower() == lowercase_target[idx]:
                    label.config(fg="#2e8b57")
                else:
                    self.stats.register_error(len(typed))
                    self.entry_var.set("")
                    for reset_label in self.letter_labels:
                        reset_label.config(fg="#b22222")
                    self._speak_current_word()
                    self.after(800, self._render_current_word)
                    self._update_status()
                    return
            else:
                label.config(fg="#1e1e1e")

        if typed.lower() == lowercase_target:
            self.stats.register_word(len(target))
            self._update_status()
            self.after(300, self._next_word)

    def _update_status(self) -> None:
        self.status_var.set(
            f"速度: {self.stats.words_per_minute:.1f} 词/分钟 | 正确率: {self.stats.accuracy * 100:.1f}%"
        )
