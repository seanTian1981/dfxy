from __future__ import annotations

import random
from typing import List, Optional

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)

from app.core.audio import TextToSpeech
from app.core.data_loader import WordEntry, load_words
from app.core.stats import PracticeStats


class WordPracticeWidget(QWidget):
    def __init__(self, tts: TextToSpeech, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.tts = tts
        self.current_level = "cet4"
        self.current_word: Optional[WordEntry] = None
        self.word_bank: dict[str, List[WordEntry]] = {
            "cet4": load_words("cet4"),
            "cet6": load_words("cet6"),
        }
        self.word_queue: List[WordEntry] = []
        self.letter_labels: List[QLabel] = []

        self.stats = PracticeStats()

        self.level_combobox: Optional[QComboBox] = None
        self.word_title_label: Optional[QLabel] = None
        self.phonetic_label: Optional[QLabel] = None
        self.meaning_label: Optional[QLabel] = None
        self.example_label: Optional[QLabel] = None
        self.entry: Optional[QLineEdit] = None
        self.status_label: Optional[QLabel] = None
        self.letters_container: Optional[QHBoxLayout] = None

        self._build_ui()
        self._reset_queue()
        self._next_word()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 16)
        layout.setSpacing(20)

        hero_label = QLabel("单词精英打字营")
        hero_label.setObjectName("TitleLabel")
        hero_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        layout.addWidget(hero_label)

        subtitle = QLabel("沉浸式美式发音体验，随时切换四级 / 六级词库，打造高效记忆节奏")
        subtitle.setStyleSheet("color: #64748b; font-size: 15px;")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        card = QFrame()
        card.setObjectName("CardFrame")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(28, 24, 28, 24)
        card_layout.setSpacing(24)
        layout.addWidget(card)

        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(18)
        card_layout.addLayout(controls_layout)

        level_caption = QLabel("选择词汇等级")
        level_caption.setObjectName("SectionHeader")
        controls_layout.addWidget(level_caption)

        level_box = QComboBox()
        level_box.addItems(["cet4", "cet6"])
        level_box.setCurrentText(self.current_level)
        level_box.currentTextChanged.connect(self._on_level_change)
        controls_layout.addWidget(level_box)
        self.level_combobox = level_box

        restart_button = QPushButton("重置练习")
        restart_button.clicked.connect(self._restart_practice)
        controls_layout.addWidget(restart_button)

        speak_button = QPushButton("播放发音")
        speak_button.clicked.connect(self._speak_current_word)
        controls_layout.addWidget(speak_button)

        controls_layout.addSpacerItem(QSpacerItem(10, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))

        word_display = QFrame()
        word_display.setObjectName("CardFrame")
        inner_layout = QVBoxLayout(word_display)
        inner_layout.setContentsMargins(26, 26, 26, 26)
        inner_layout.setSpacing(18)
        card_layout.addWidget(word_display)

        self.word_title_label = QLabel("")
        self.word_title_label.setAlignment(Qt.AlignCenter)
        self.word_title_label.setStyleSheet("font-size: 38px; font-weight: 800;")
        inner_layout.addWidget(self.word_title_label)

        self.phonetic_label = QLabel("")
        self.phonetic_label.setAlignment(Qt.AlignCenter)
        self.phonetic_label.setStyleSheet("font-size: 20px; color: #1a73e8;")
        inner_layout.addWidget(self.phonetic_label)

        self.meaning_label = QLabel("")
        self.meaning_label.setWordWrap(True)
        self.meaning_label.setAlignment(Qt.AlignCenter)
        self.meaning_label.setStyleSheet("font-size: 16px;")
        inner_layout.addWidget(self.meaning_label)

        self.example_label = QLabel("")
        self.example_label.setWordWrap(True)
        self.example_label.setAlignment(Qt.AlignCenter)
        self.example_label.setStyleSheet("color: #475569; font-size: 15px;")
        inner_layout.addWidget(self.example_label)

        letter_frame = QFrame()
        letter_layout = QHBoxLayout(letter_frame)
        letter_layout.setContentsMargins(0, 12, 0, 12)
        letter_layout.setSpacing(10)
        letter_layout.setAlignment(Qt.AlignCenter)
        inner_layout.addWidget(letter_frame)
        self.letters_container = letter_layout

        entry = QLineEdit()
        entry.setPlaceholderText("请在此输入单词，系统将实时点评您的准确率")
        entry.setAlignment(Qt.AlignCenter)
        entry.setStyleSheet("font-size: 22px; font-weight: 600;")
        entry.textChanged.connect(self._on_input_change)
        inner_layout.addWidget(entry)
        self.entry = entry

        status = QLabel("速度: 0.0 词/分钟 | 正确率: 100.0%")
        status.setObjectName("StatusLabel")
        status.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        layout.addWidget(status)
        self.status_label = status

    def _on_level_change(self, level: str) -> None:
        if level == self.current_level:
            return
        self.current_level = level
        self._restart_practice()

    def _restart_practice(self) -> None:
        self._reset_queue()
        self._next_word()

    def _reset_queue(self) -> None:
        base_list = self.word_bank[self.current_level][:]
        random.shuffle(base_list)
        self.word_queue = base_list
        self.stats.reset()
        self._update_status()

    def _next_word(self) -> None:
        if not self.word_queue:
            QMessageBox.information(self, "练习完成", "该等级的全部单词已练习完毕，系统将为您重新随机排列。")
            self._reset_queue()
        self.current_word = self.word_queue.pop()
        if self.entry is not None:
            self.entry.blockSignals(True)
            self.entry.clear()
            self.entry.blockSignals(False)
            self.entry.setFocus()
        self._render_current_word()
        QTimer.singleShot(300, self._speak_current_word)

    def _render_current_word(self) -> None:
        if self.current_word is None or self.letters_container is None:
            return
        while self.letter_labels:
            label = self.letter_labels.pop()
            label.deleteLater()
        self.letters_container.setSpacing(10)

        font = QFont()
        font.setPointSize(30)
        font.setBold(True)

        for char in self.current_word.word:
            lbl = QLabel(char.upper())
            lbl.setFont(font)
            lbl.setStyleSheet("color: #1e293b; padding: 6px 8px;")
            self.letters_container.addWidget(lbl)
            self.letter_labels.append(lbl)

        if self.word_title_label is not None:
            self.word_title_label.setText(self.current_word.word.upper())
        if self.phonetic_label is not None:
            self.phonetic_label.setText(self.current_word.phonetic)
        if self.meaning_label is not None:
            self.meaning_label.setText(f"释义：{self.current_word.meaning}")
        if self.example_label is not None:
            self.example_label.setText(f"例句：{self.current_word.example}")

        for label in self.letter_labels:
            label.setStyleSheet("color: #1e293b; padding: 6px 8px;")

    def _speak_current_word(self) -> None:
        if self.current_word is None:
            return
        utterance = f"{self.current_word.word}. {self.current_word.meaning}"
        self.tts.speak(utterance)

    def _on_input_change(self, text: str) -> None:
        if self.current_word is None:
            return
        target = self.current_word.word
        lowercase_target = target.lower()

        if not text:
            for label in self.letter_labels:
                label.setStyleSheet("color: #1e293b; padding: 6px 8px;")
            return

        for idx, label in enumerate(self.letter_labels):
            if idx < len(text):
                if text[idx].lower() == lowercase_target[idx]:
                    label.setStyleSheet("color: #16a34a; padding: 6px 8px;")
                else:
                    self.stats.register_error(len(text))
                    if self.entry is not None:
                        self.entry.blockSignals(True)
                        self.entry.clear()
                        self.entry.blockSignals(False)
                    for reset_label in self.letter_labels:
                        reset_label.setStyleSheet("color: #dc2626; padding: 6px 8px;")
                    QTimer.singleShot(800, self._render_current_word)
                    QTimer.singleShot(600, self._speak_current_word)
                    self._update_status()
                    return
            else:
                label.setStyleSheet("color: #1e293b; padding: 6px 8px;")

        if text.lower() == lowercase_target:
            self.stats.register_word(len(target))
            self._update_status()
            QTimer.singleShot(350, self._next_word)

    def _update_status(self) -> None:
        if self.status_label is None:
            return
        self.status_label.setText(
            f"速度: {self.stats.words_per_minute:.1f} 词/分钟 | 正确率: {self.stats.accuracy * 100:.1f}%"
        )
