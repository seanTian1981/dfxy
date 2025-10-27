from __future__ import annotations

import random
from dataclasses import dataclass
from html import escape
from typing import List, Optional

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)

from app.core.data_loader import Essay, load_essays
from app.core.stats import EssayStats


@dataclass
class EssayLineWidget:
    reference_label: QLabel
    input_field: QLineEdit
    target_text: str


class EssayPracticeWidget(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.essays: List[Essay] = load_essays()
        self.current_essay: Optional[Essay] = None
        self.target_text: str = ""
        self.target_lines: List[str] = []
        self.stats = EssayStats()
        self.current_font_size = 16

        self.title_label: Optional[QLabel] = None
        self.status_label: Optional[QLabel] = None
        self.scroll_area: Optional[QScrollArea] = None
        self.lines_container: Optional[QVBoxLayout] = None
        self.font_slider: Optional[QSlider] = None

        self.line_widgets: List[EssayLineWidget] = []

        self._build_ui()
        self._load_random_essay()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 16)
        layout.setSpacing(20)

        title_row = QHBoxLayout()
        title_row.setSpacing(16)
        layout.addLayout(title_row)

        title = QLabel("优秀论文沉浸练习")
        title.setObjectName("TitleLabel")
        title_row.addWidget(title)
        self.title_label = QLabel("")
        self.title_label.setStyleSheet("font-size: 20px; font-weight: 600; color: #1a73e8;")
        self.title_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        title_row.addWidget(self.title_label, stretch=1)

        title_row.addSpacerItem(QSpacerItem(20, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))

        font_hint = QLabel("字体大小")
        font_hint.setStyleSheet("color: #64748b; font-size: 14px;")
        title_row.addWidget(font_hint)

        slider = QSlider(Qt.Horizontal)
        slider.setMinimum(12)
        slider.setMaximum(28)
        slider.setValue(self.current_font_size)
        slider.setFixedWidth(160)
        slider.setTickInterval(2)
        slider.setSingleStep(1)
        slider.setTickPosition(QSlider.TicksBelow)
        slider.valueChanged.connect(self._on_font_size_changed)
        title_row.addWidget(slider)
        self.font_slider = slider

        random_button = QPushButton("换一篇灵感佳作")
        random_button.clicked.connect(self._load_random_essay)
        title_row.addWidget(random_button)

        subtitle = QLabel("逐行对照练习，实时反馈用词精准度，支持自定义字体大小打造最舒适的练习体验")
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color: #64748b; font-size: 15px;")
        layout.addWidget(subtitle)

        outer_card = QFrame()
        outer_card.setObjectName("CardFrame")
        outer_layout = QVBoxLayout(outer_card)
        outer_layout.setContentsMargins(20, 20, 20, 20)
        outer_layout.setSpacing(18)
        layout.addWidget(outer_card)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        outer_layout.addWidget(scroll)
        self.scroll_area = scroll

        scroll_widget = QWidget()
        scroll.setWidget(scroll_widget)
        lines_layout = QVBoxLayout(scroll_widget)
        lines_layout.setContentsMargins(0, 0, 0, 0)
        lines_layout.setSpacing(16)
        self.lines_container = lines_layout

        status = QLabel("速度: 0.0 词/分钟 | 正确率: 100.0%")
        status.setObjectName("StatusLabel")
        status.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        layout.addWidget(status)
        self.status_label = status

    def _on_font_size_changed(self, value: int) -> None:
        self.current_font_size = value
        self._apply_font_size()

    def _apply_font_size(self) -> None:
        for widget in self.line_widgets:
            font = widget.input_field.font()
            font.setPointSize(self.current_font_size)
            widget.input_field.setFont(font)
            self._update_label_color(widget)

    def _load_random_essay(self) -> None:
        if not self.essays:
            return
        self.current_essay = random.choice(self.essays)
        self.target_text = self.current_essay.content.strip()
        self.target_lines = self._split_lines(self.target_text)
        self.stats.reset()
        if self.title_label is not None:
            self.title_label.setText(self.current_essay.title)
        self._render_lines()
        self._update_status()
        if self.scroll_area is not None:
            self.scroll_area.verticalScrollBar().setValue(0)

    def _render_lines(self) -> None:
        if self.lines_container is None:
            return
        # Clear existing widgets
        self.line_widgets.clear()
        while self.lines_container.count():
            item = self.lines_container.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        for index, line_text in enumerate(self.target_lines):
            line_card = QFrame()
            line_card.setObjectName("CardFrame")
            line_card.setStyleSheet("border-radius: 14px; background-color: #fff;")
            line_layout = QVBoxLayout(line_card)
            line_layout.setContentsMargins(18, 16, 18, 16)
            line_layout.setSpacing(12)

            ref_label = QLabel()
            ref_label.setWordWrap(True)
            ref_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
            ref_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            ref_label.setTextFormat(Qt.RichText)
            line_layout.addWidget(ref_label)

            input_field = QLineEdit()
            input_field.setPlaceholderText("请逐行跟随范文输入，系统实时判别正确率")
            input_field.textChanged.connect(lambda text, idx=index: self._on_line_changed(idx, text))
            input_field.returnPressed.connect(lambda idx=index: self._focus_next(idx))
            line_layout.addWidget(input_field)

            widget = EssayLineWidget(reference_label=ref_label, input_field=input_field, target_text=line_text)
            self.lines_container.addWidget(line_card)
            self.line_widgets.append(widget)
            self._update_label_color(widget)

        self.lines_container.addStretch(1)
        self._apply_font_size()
        self._focus_first_entry()

    def _focus_first_entry(self) -> None:
        if not self.line_widgets:
            return
        first_entry = self.line_widgets[0].input_field
        QTimer.singleShot(100, first_entry.setFocus)

    def _focus_next(self, index: int) -> None:
        next_index = index + 1
        if 0 <= next_index < len(self.line_widgets):
            next_entry = self.line_widgets[next_index].input_field
            QTimer.singleShot(0, next_entry.setFocus)

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

    def _update_label_color(self, widget: EssayLineWidget) -> None:
        typed_text = widget.input_field.text()
        target_line = widget.target_text
        typed_length = len(typed_text)

        segments: List[str] = []
        for idx, char in enumerate(target_line):
            if idx < typed_length:
                if typed_text[idx] == char:
                    color = "#16a34a"
                else:
                    color = "#dc2626"
            else:
                color = "#1e293b"

            safe_char = escape(char)
            segments.append(f'<span style="color: {color};">{safe_char}</span>')

        styled_text = (
            f'<div style="font-size: {self.current_font_size}px; font-weight: 500; '
            f'line-height: 1.6; white-space: pre-wrap;">{"".join(segments)}</div>'
        )
        widget.reference_label.setText(styled_text)

    def _on_line_changed(self, index: int, _text: str) -> None:
        if not (0 <= index < len(self.line_widgets)):
            return
        widget = self.line_widgets[index]
        self._update_label_color(widget)

        self._refresh_stats_and_status()

    def _refresh_stats_and_status(self) -> None:
        typed_segments = [widget.input_field.text().strip() for widget in self.line_widgets]
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
        if self.status_label is None:
            return
        accuracy = 100.0 if self.stats.total_letters == 0 else self.stats.accuracy * 100
        self.status_label.setText(
            f"速度: {self.stats.words_per_minute:.1f} 词/分钟 | 正确率: {accuracy:.1f}%"
        )
