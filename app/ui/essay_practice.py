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

        self.style = ttk.Style()
        self.default_label_fg = self.style.lookup("TLabel", "foreground") or "#1f2933"

        self.line_labels: List[ttk.Label] = []
        self.line_entries: List[ttk.Entry] = []
        self.line_vars: List[tk.StringVar] = []

        self._build_ui()
        self._load_random_essay()

    def _build_ui(self) -> None:
        top_bar = ttk.Frame(self)
        top_bar.pack(fill=tk.X, padx=12, pady=(12, 8))

        ttk.Button(top_bar, text="随机优秀作文", command=self._load_random_essay).pack(side=tk.LEFT)

        self.title_var = tk.StringVar(value="")
        ttk.Label(top_bar, textvariable=self.title_var, font=("Helvetica", 16, "bold")).pack(
            side=tk.LEFT, padx=16
        )

        practice_frame = ttk.Frame(self)
        practice_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))

        header = ttk.Label(
            practice_frame,
            text="参考范文逐行练习",
            font=("Helvetica", 12, "bold"),
        )
        header.pack(anchor=tk.W, pady=(0, 6))

        canvas_container = ttk.Frame(practice_frame)
        canvas_container.pack(fill=tk.BOTH, expand=True)

        self.line_canvas = tk.Canvas(canvas_container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_container, orient=tk.VERTICAL, command=self.line_canvas.yview)
        self.line_canvas.configure(yscrollcommand=scrollbar.set)

        self.line_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.lines_container = ttk.Frame(self.line_canvas)
        self.canvas_window = self.line_canvas.create_window((0, 0), window=self.lines_container, anchor="nw")

        self.lines_container.bind(
            "<Configure>", lambda event: self.line_canvas.configure(scrollregion=self.line_canvas.bbox("all"))
        )
        self.line_canvas.bind(
            "<Configure>", lambda event: self.line_canvas.itemconfigure(self.canvas_window, width=event.width)
        )

        self.status_label = ttk.Label(self, textvariable=self.status_var, anchor=tk.W)
        self.status_label.pack(fill=tk.X, side=tk.BOTTOM, padx=12, pady=4)

    def _load_random_essay(self) -> None:
        self.current_essay = random.choice(self.essays)
        self.title_var.set(self.current_essay.title)
        self.target_text = self.current_essay.content.strip()
        self.target_lines = self._split_lines(self.target_text)
        self.stats.reset()
        self._render_reference()
        self._update_status()

    def _render_reference(self) -> None:
        for child in self.lines_container.winfo_children():
            child.destroy()

        self.line_labels.clear()
        self.line_entries.clear()
        self.line_vars.clear()

        for idx, line in enumerate(self.target_lines):
            line_frame = ttk.Frame(self.lines_container, padding=(0, 8))
            line_frame.pack(fill=tk.X, expand=True)

            label_text = line
            label = ttk.Label(
                line_frame,
                text=label_text,
                wraplength=720,
                justify=tk.LEFT,
                font=("Helvetica", 12),
                foreground=self.default_label_fg,
            )
            label.pack(fill=tk.X, anchor=tk.W)

            entry_var = tk.StringVar()
            entry = ttk.Entry(line_frame, textvariable=entry_var, font=("Helvetica", 12))
            entry.pack(fill=tk.X, pady=(6, 0))

            entry.bind("<KeyRelease>", lambda _event, i=idx: self._on_line_changed(i))
            entry.bind("<FocusOut>", lambda _event, i=idx: self._on_line_changed(i))
            entry.bind("<Return>", lambda event, i=idx: self._focus_next_entry(event, i))

            self.line_labels.append(label)
            self.line_vars.append(entry_var)
            self.line_entries.append(entry)

        self.after_idle(self._focus_first_entry)
        self.line_canvas.yview_moveto(0.0)
        bbox = self.line_canvas.bbox("all")
        if bbox:
            self.line_canvas.configure(scrollregion=bbox)

    def _focus_first_entry(self) -> None:
        if self.line_entries:
            self.line_entries[0].focus_set()
            self.line_entries[0].icursor(tk.END)

    def _focus_next_entry(self, event: tk.Event, index: int) -> str:
        next_index = index + 1
        if next_index < len(self.line_entries):
            self.line_entries[next_index].focus_set()
            self.line_entries[next_index].icursor(tk.END)
        return "break"

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

    def _on_line_changed(self, index: int) -> None:
        if index >= len(self.line_vars):
            return

        typed_text = self.line_vars[index].get().strip()
        target_line = self.target_lines[index].strip()

        if not typed_text:
            self.line_labels[index].configure(foreground=self.default_label_fg)
        elif typed_text == target_line:
            self.line_labels[index].configure(foreground="#2e8b57")
        else:
            self.line_labels[index].configure(foreground="#b22222")

        self._refresh_stats_and_status()

    def _refresh_stats_and_status(self) -> None:
        typed_segments = [var.get().strip() for var in self.line_vars]
        typed_text = "\n".join(typed_segments).rstrip()
        target = "\n".join(self.target_lines).rstrip()

        correct_chars = 0
        total_chars = len(typed_text)
        compare_length = min(len(typed_text), len(target))

        for idx in range(compare_length):
            if typed_text[idx] == target[idx]:
                correct_chars += 1

        self.stats.correct_letters = correct_chars
        self.stats.total_letters = total_chars
        self._update_status()

        if target and typed_text == target:
            self.stats.register_completion(len(target))
            self._update_status()

    def _update_status(self) -> None:
        accuracy = 100.0 if self.stats.total_letters == 0 else self.stats.accuracy * 100
        self.status_var.set(
            f"速度: {self.stats.words_per_minute:.1f} 词/分钟 | 正确率: {accuracy:.1f}%"
        )
