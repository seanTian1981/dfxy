from __future__ import annotations

import random
import tkinter as tk
from tkinter import ttk
from typing import List

from app.core.data_loader import Essay, load_essays
from app.core.stats import EssayStats


class EssayPracticeFrame(ttk.Frame):
    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master)
        self.essays: List[Essay] = load_essays()
        self.current_essay: Essay | None = None
        self.target_text: str = ""
        self.target_lines: List[str] = []
        self.stats = EssayStats()
        self.status_var = tk.StringVar(value="速度: 0.0 词/分钟 | 正确率: 100.0%")

        self._build_ui()
        self._load_random_essay()

    def _build_ui(self) -> None:
        top_bar = ttk.Frame(self)
        top_bar.pack(fill=tk.X, padx=12, pady=8)

        ttk.Button(top_bar, text="随机优秀作文", command=self._load_random_essay).pack(side=tk.LEFT)

        self.title_var = tk.StringVar(value="")
        ttk.Label(top_bar, textvariable=self.title_var, font=("Helvetica", 16, "bold")).pack(
            side=tk.LEFT, padx=16
        )

        work_frame = ttk.Panedwindow(self, orient=tk.VERTICAL)
        work_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        reference_frame = ttk.Frame(work_frame)
        work_frame.add(reference_frame, weight=1)

        ttk.Label(reference_frame, text="参考范文", font=("Helvetica", 12, "bold")).pack(anchor=tk.W)
        self.reference_text = tk.Text(reference_frame, height=12, wrap=tk.WORD, state=tk.DISABLED)
        self.reference_text.pack(fill=tk.BOTH, expand=True, pady=(4, 8))

        input_frame = ttk.Frame(work_frame)
        work_frame.add(input_frame, weight=1)

        ttk.Label(input_frame, text="请输入范文 (每行约10-15词)", font=("Helvetica", 12, "bold")).pack(
            anchor=tk.W
        )
        self.user_text = tk.Text(input_frame, height=12, wrap=tk.WORD)
        self.user_text.pack(fill=tk.BOTH, expand=True, pady=(4, 8))
        self.user_text.bind("<KeyRelease>", self._on_text_changed)

        self.user_text.tag_configure("correct", foreground="#2e8b57")
        self.user_text.tag_configure("incorrect", foreground="#b22222")

        self.status_label = ttk.Label(self, textvariable=self.status_var, anchor=tk.W)
        self.status_label.pack(fill=tk.X, side=tk.BOTTOM, padx=12, pady=4)

    def _load_random_essay(self) -> None:
        self.current_essay = random.choice(self.essays)
        self.title_var.set(self.current_essay.title)
        self.target_text = self.current_essay.content.strip()
        self.target_lines = self._split_lines(self.target_text)
        self._render_reference()
        self.stats.reset()
        self.user_text.delete("1.0", tk.END)
        self._update_status()

    def _render_reference(self) -> None:
        combined = "\n".join(self.target_lines)
        self.reference_text.configure(state=tk.NORMAL)
        self.reference_text.delete("1.0", tk.END)
        self.reference_text.insert("1.0", combined)
        self.reference_text.configure(state=tk.DISABLED)

    @staticmethod
    def _split_lines(text: str) -> List[str]:
        words = text.split()
        lines: List[str] = []
        current: List[str] = []
        for word in words:
            current.append(word)
            if len(current) >= 12:
                lines.append(" ".join(current))
                current = []
        if current:
            lines.append(" ".join(current))
        return lines

    def _on_text_changed(self, _event: tk.Event | None = None) -> None:
        typed = self.user_text.get("1.0", tk.END).rstrip()
        target = "\n".join(self.target_lines)

        self.user_text.tag_remove("correct", "1.0", tk.END)
        self.user_text.tag_remove("incorrect", "1.0", tk.END)

        correct_chars = 0
        total_chars = len(typed)
        compare_length = min(len(typed), len(target))

        for idx in range(compare_length):
            start = self._offset_to_index(idx)
            end = self._offset_to_index(idx + 1)
            if typed[idx] == target[idx]:
                self.user_text.tag_add("correct", start, end)
                correct_chars += 1
            else:
                self.user_text.tag_add("incorrect", start, end)
        for idx in range(compare_length, len(typed)):
            start = self._offset_to_index(idx)
            end = self._offset_to_index(idx + 1)
            self.user_text.tag_add("incorrect", start, end)

        self.stats.correct_letters = correct_chars
        self.stats.total_letters = total_chars
        self._update_status()

        if typed == target and target:
            self.stats.register_completion(len(target))
            self._update_status()

    def _offset_to_index(self, offset: int) -> str:
        return f"1.0+{offset}c"

    def _update_status(self) -> None:
        accuracy = 100.0 if self.stats.total_letters == 0 else self.stats.accuracy * 100
        self.status_var.set(
            f"速度: {self.stats.words_per_minute:.1f} 词/分钟 | 正确率: {accuracy:.1f}%"
        )
