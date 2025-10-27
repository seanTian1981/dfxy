from __future__ import annotations

import sys
from typing import Optional

from PyQt5.QtCore import QSize
from PyQt5.QtGui import QColor, QPalette
from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget

from app.core.audio import TextToSpeech
from app.ui.essay_practice import EssayPracticeWidget
from app.ui.pk_mode import PkModeWidget
from app.ui.word_practice import WordPracticeWidget


def _apply_global_theme(app: QApplication) -> None:
    app.setStyle("Fusion")

    ultra_light = QColor("#f4f6fb")
    surface = QColor("#ffffff")
    primary = QColor("#1a73e8")
    text_primary = QColor("#1f2933")

    palette = QPalette()
    palette.setColor(QPalette.Window, ultra_light)
    palette.setColor(QPalette.WindowText, text_primary)
    palette.setColor(QPalette.Base, surface)
    palette.setColor(QPalette.AlternateBase, QColor("#eef2fb"))
    palette.setColor(QPalette.ToolTipBase, surface)
    palette.setColor(QPalette.ToolTipText, text_primary)
    palette.setColor(QPalette.Text, text_primary)
    palette.setColor(QPalette.Button, surface)
    palette.setColor(QPalette.ButtonText, text_primary)
    palette.setColor(QPalette.Highlight, primary)
    palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))
    app.setPalette(palette)

    app.setStyleSheet(
        """
        QWidget {
            font-family: "Microsoft YaHei", "Source Han Sans", "Helvetica Neue", Arial, sans-serif;
            font-size: 14px;
            color: #1f2933;
        }
        QMainWindow {
            background-color: #f4f6fb;
        }
        QFrame#CardFrame {
            background-color: #ffffff;
            border-radius: 18px;
            border: 1px solid rgba(26,115,232,0.08);
        }
        QPushButton {
            background-color: #1a73e8;
            color: #ffffff;
            border-radius: 10px;
            padding: 8px 18px;
            font-weight: 600;
        }
        QPushButton:hover {
            background-color: #1557b0;
        }
        QPushButton:disabled {
            background-color: #cbd6ee;
            color: #ffffff;
        }
        QComboBox, QLineEdit, QTextEdit, QSpinBox {
            border: 1px solid #d0d7e3;
            border-radius: 10px;
            padding: 6px 12px;
            background-color: #ffffff;
        }
        QListWidget, QScrollArea {
            border: 1px solid #d0d7e3;
            border-radius: 14px;
            background-color: #ffffff;
        }
        QTabWidget::pane {
            border: none;
        }
        QTabBar::tab {
            background: #e8ecf5;
            color: #4a5568;
            border-top-left-radius: 14px;
            border-top-right-radius: 14px;
            padding: 10px 22px;
            margin-right: 6px;
            font-weight: 600;
        }
        QTabBar::tab:selected {
            background: #ffffff;
            color: #1a73e8;
        }
        QLabel#TitleLabel {
            font-size: 28px;
            font-weight: 700;
            color: #1f2933;
        }
        QLabel#SectionHeader {
            font-size: 16px;
            font-weight: 600;
            color: #334155;
        }
        QLabel#StatusLabel {
            color: #1a73e8;
            font-weight: 600;
        }
        """
    )


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.tts = TextToSpeech()
        self.word_tab: Optional[WordPracticeWidget] = None
        self.essay_tab: Optional[EssayPracticeWidget] = None
        self.pk_tab: Optional[PkModeWidget] = None

        self.setWindowTitle("英语四六级打字练习系统")
        self.resize(1100, 780)
        self.setMinimumSize(QSize(960, 640))

        self._tab_widget = QTabWidget()
        self._tab_widget.setDocumentMode(True)
        self._tab_widget.setMovable(False)
        self._tab_widget.setTabBarAutoHide(False)
        self.setCentralWidget(self._tab_widget)

        self._build_tabs()

    def _build_tabs(self) -> None:
        self.word_tab = WordPracticeWidget(tts=self.tts, parent=self)
        self.essay_tab = EssayPracticeWidget(parent=self)
        self.pk_tab = PkModeWidget(parent=self)

        self._tab_widget.addTab(self.word_tab, "单词打字练习")
        self._tab_widget.addTab(self.essay_tab, "优秀作文练习")
        self._tab_widget.addTab(self.pk_tab, "PK 对战")

    def closeEvent(self, event) -> None:  # type: ignore[override]
        if self.pk_tab is not None:
            self.pk_tab.shutdown()
        self.tts.shutdown()
        super().closeEvent(event)


def run() -> None:
    app = QApplication(sys.argv)
    _apply_global_theme(app)
    window = MainWindow()
    window.show()
    app.exec_()
