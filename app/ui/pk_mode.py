from __future__ import annotations

import json
import queue
import re
from typing import Dict, Optional

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QTextCharFormat, QTextCursor
from PyQt5.QtWidgets import (
    QDialog,
    QFrame,
    QGridLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.core.stats import EssayStats
from app.network.pk_client import PkClient
from app.network.pk_server import PK_PORT, PkServer

BANNED_KEYWORDS = {"傻", "笨", "蠢", "操", "妈", "垃圾", "滚", "死"}


class PkModeWidget(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.server: Optional[PkServer] = None
        self.client: Optional[PkClient] = None
        self.message_queue: "queue.Queue[dict]" = queue.Queue()
        self.users: Dict[str, str] = {}
        self.current_challenge_id: Optional[str] = None
        self.challenge_dialog: Optional[ChallengeDialog] = None

        self.student_id_input: Optional[QLineEdit] = None
        self.name_input: Optional[QLineEdit] = None
        self.connect_button: Optional[QPushButton] = None
        self.disconnect_button: Optional[QPushButton] = None
        self.status_label: Optional[QLabel] = None
        self.user_list: Optional[QListWidget] = None

        self._build_ui()
        self._ensure_server()

        self._message_timer = QTimer(self)
        self._message_timer.timeout.connect(self._process_messages)
        self._message_timer.start(200)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 16)
        layout.setSpacing(20)

        hero = QLabel("实时 PK 互动大厅")
        hero.setObjectName("TitleLabel")
        layout.addWidget(hero)

        subtitle = QLabel(
            "与同伴实时联机，体验竞技式写作比拼。支持本地服务器自动启动，双击在线用户即可发起挑战。"
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color: #64748b; font-size: 15px;")
        layout.addWidget(subtitle)

        card = QFrame()
        card.setObjectName("CardFrame")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(22)
        layout.addWidget(card)

        form_grid = QGridLayout()
        form_grid.setHorizontalSpacing(18)
        form_grid.setVerticalSpacing(12)
        card_layout.addLayout(form_grid)

        student_label = QLabel("学号 (8位数字)")
        student_label.setObjectName("SectionHeader")
        form_grid.addWidget(student_label, 0, 0)

        student_edit = QLineEdit()
        student_edit.setPlaceholderText("请输入 8 位数字学号")
        form_grid.addWidget(student_edit, 0, 1)
        self.student_id_input = student_edit

        name_label = QLabel("姓名 (2-4 个中文字符)")
        name_label.setObjectName("SectionHeader")
        form_grid.addWidget(name_label, 0, 2)

        name_edit = QLineEdit()
        name_edit.setPlaceholderText("请输入规范中文姓名")
        form_grid.addWidget(name_edit, 0, 3)
        self.name_input = name_edit

        connect_btn = QPushButton("连接大厅")
        connect_btn.clicked.connect(self._on_connect)
        form_grid.addWidget(connect_btn, 0, 4)
        self.connect_button = connect_btn

        disconnect_btn = QPushButton("断开连接")
        disconnect_btn.setEnabled(False)
        disconnect_btn.clicked.connect(self._on_disconnect)
        form_grid.addWidget(disconnect_btn, 0, 5)
        self.disconnect_button = disconnect_btn

        status = QLabel("未连接")
        status.setObjectName("StatusLabel")
        card_layout.addWidget(status)
        self.status_label = status

        list_card = QFrame()
        list_card.setObjectName("CardFrame")
        list_layout = QVBoxLayout(list_card)
        list_layout.setContentsMargins(20, 20, 20, 20)
        list_layout.setSpacing(12)
        card_layout.addWidget(list_card, stretch=1)

        list_header = QLabel("在线用户 · 双击昵称即可发起挑战")
        list_header.setObjectName("SectionHeader")
        list_layout.addWidget(list_header)

        user_list = QListWidget()
        user_list.setObjectName("CardFrame")
        user_list.setSpacing(6)
        user_list.itemDoubleClicked.connect(self._on_user_double_click)
        list_layout.addWidget(user_list, stretch=1)
        self.user_list = user_list

    def _ensure_server(self) -> None:
        try:
            server = PkServer()
            server.start()
            self.server = server
            self._set_status(f"已自动启动本地对战服务器 (端口 {PK_PORT})")
        except OSError:
            self.server = None
            self._set_status(f"检测到已有服务器，准备连接 (端口 {PK_PORT})")

    def _set_status(self, text: str) -> None:
        if self.status_label is not None:
            self.status_label.setText(text)

    def _on_connect(self) -> None:
        if self.student_id_input is None or self.name_input is None:
            return
        student_id = self.student_id_input.text().strip()
        name = self.name_input.text().strip()

        if not re.fullmatch(r"\d{8}", student_id):
            QMessageBox.warning(self, "输入错误", "学号必须是 8 位数字")
            return
        if not (2 <= len(name) <= 4) or not all("\u4e00" <= ch <= "\u9fff" for ch in name):
            QMessageBox.warning(self, "输入错误", "姓名必须为 2-4 个中文字符")
            return
        if any(keyword in name for keyword in BANNED_KEYWORDS):
            QMessageBox.warning(self, "输入错误", "请勿使用不文明的称呼")
            return

        if self.client is None:
            self.client = PkClient(on_message=self.message_queue.put)

        self.client.register(student_id, name)
        if self.connect_button is not None:
            self.connect_button.setEnabled(False)
        if self.disconnect_button is not None:
            self.disconnect_button.setEnabled(True)
        self._set_status("已连接，正在同步在线用户...")

    def _on_disconnect(self) -> None:
        if self.client is not None:
            self.client.deregister()
            self.client.close()
            self.client = None
        self.users.clear()
        self._refresh_user_list()
        if self.connect_button is not None:
            self.connect_button.setEnabled(True)
        if self.disconnect_button is not None:
            self.disconnect_button.setEnabled(False)
        self._set_status("已断开连接")

    def _process_messages(self) -> None:
        try:
            while True:
                message = self.message_queue.get_nowait()
                self._handle_message(message)
        except queue.Empty:
            return

    def _handle_message(self, message: dict) -> None:
        msg_type = message.get("type")
        if msg_type == "user_list":
            self._handle_user_list(message)
        elif msg_type == "challenge_request":
            self._handle_challenge_request(message)
        elif msg_type == "challenge_response":
            self._handle_challenge_response(message)
        elif msg_type == "start_challenge":
            self._handle_start_challenge(message)
        elif msg_type == "challenge_result":
            self._handle_challenge_result(message)

    def _handle_user_list(self, message: dict) -> None:
        users = message.get("users", [])
        my_id = self.client.student_id if self.client else None
        self.users = {
            user["student_id"]: user["name"]
            for user in users
            if user["student_id"] != my_id
        }
        self._refresh_user_list()
        self._set_status(f"当前在线 {len(users)} 人")

    def _refresh_user_list(self) -> None:
        if self.user_list is None:
            return
        self.user_list.clear()
        for student_id, name in self.users.items():
            item = QListWidgetItem(f"{name} ({student_id})")
            self.user_list.addItem(item)

    def _on_user_double_click(self, item: QListWidgetItem) -> None:
        if self.client is None or item is None:
            return
        index = self.user_list.row(item) if self.user_list else -1
        if index < 0:
            return
        student_id = list(self.users.keys())[index]
        self.client.request_challenge(student_id)
        self._set_status(f"已向 {self.users[student_id]} 发起挑战，等待回应...")

    def _handle_challenge_request(self, message: dict) -> None:
        challenger = message.get("from", {})
        challenger_name = challenger.get("name", "未知")
        challenger_id = challenger.get("student_id", "")
        if not challenger_id or self.client is None:
            return
        reply = QMessageBox.question(
            self,
            "收到挑战",
            f"{challenger_name} 向您发起挑战，是否接受？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        accept = reply == QMessageBox.Yes
        self.client.respond_challenge(challenger_id, accept)
        if accept:
            self._set_status(f"已接受 {challenger_name} 的挑战，准备开始...")
        else:
            QMessageBox.information(self, "提示", "您已拒绝对方的挑战")
            self._set_status(f"已拒绝 {challenger_name} 的挑战")

    def _handle_challenge_response(self, message: dict) -> None:
        accepted = message.get("accepted", False)
        responder = message.get("from", {})
        responder_name = responder.get("name", "对方")
        if accepted:
            self._set_status(f"{responder_name} 接受了您的挑战，准备中...")
        else:
            QMessageBox.information(self, "提示", "对方不接受您的挑战")
            self._set_status(f"{responder_name} 拒绝了挑战")

    def _handle_start_challenge(self, message: dict) -> None:
        if self.client is None:
            return
        challenge_id = message.get("challenge_id")
        essay = message.get("essay", {})
        self.current_challenge_id = challenge_id

        if self.challenge_dialog is not None:
            self.challenge_dialog.close()

        self.challenge_dialog = ChallengeDialog(
            client=self.client,
            challenge_id=challenge_id,
            essay_title=essay.get("title", "PK 练习"),
            essay_content=essay.get("content", ""),
            parent=self,
        )
        self.challenge_dialog.destroyed.connect(self._on_challenge_dialog_closed)
        self.challenge_dialog.show()
        self._set_status("挑战开始，祝您好运！")

    def _on_challenge_dialog_closed(self, _obj=None) -> None:
        self.challenge_dialog = None

    def _handle_challenge_result(self, message: dict) -> None:
        challenge_id = message.get("challenge_id")
        if challenge_id != self.current_challenge_id:
            return
        winner = message.get("winner")
        results = message.get("results", {})
        my_id = self.client.student_id if self.client else None
        if self.challenge_dialog is not None:
            self.challenge_dialog.show_result(winner, results, my_id)
        else:
            self._show_result_popup(winner, results, my_id)
        self.current_challenge_id = None

    def _show_result_popup(self, winner: Optional[str], results: dict, my_id: Optional[str]) -> None:
        if winner is None:
            text = "挑战结果：双方平局"
        elif winner == my_id:
            text = "挑战结果：您获胜了！"
        else:
            text = "挑战结果：对方获胜"
        details = json.dumps(results, ensure_ascii=False, indent=2)
        QMessageBox.information(self, "挑战结果", f"{text}\n详细数据:\n{details}")

    def shutdown(self) -> None:
        if self._message_timer.isActive():
            self._message_timer.stop()
        if self.challenge_dialog is not None:
            self.challenge_dialog.close()
            self.challenge_dialog = None
        if self.client is not None:
            self.client.deregister()
            self.client.close()
            self.client = None
        if self.server is not None:
            self.server.stop()
            self.server.join(timeout=1)
            self.server = None


class ChallengeDialog(QDialog):
    def __init__(
        self,
        client: PkClient,
        challenge_id: str,
        essay_title: str,
        essay_content: str,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.client = client
        self.challenge_id = challenge_id
        self.essay_title = essay_title
        self.essay_content = essay_content.strip()
        self.stats = EssayStats()
        self.submitted = False
        self.countdown_value = 5

        self.setWindowTitle("四六级作文 PK")
        self.resize(820, 620)

        self.title_label: Optional[QLabel] = None
        self.countdown_label: Optional[QLabel] = None
        self.reference_text: Optional[QTextEdit] = None
        self.user_text: Optional[QTextEdit] = None
        self.status_label: Optional[QLabel] = None
        self.result_label: Optional[QLabel] = None

        self._build_ui()
        self._render_reference()
        self._start_countdown()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title_label = QLabel(self.essay_title)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 24px; font-weight: 700; color: #1f2933;")
        layout.addWidget(title_label)
        self.title_label = title_label

        countdown_label = QLabel("挑战将在 5 秒后开始")
        countdown_label.setAlignment(Qt.AlignCenter)
        countdown_label.setStyleSheet("color: #1a73e8; font-size: 16px; font-weight: 600;")
        layout.addWidget(countdown_label)
        self.countdown_label = countdown_label

        panel = QFrame()
        panel.setObjectName("CardFrame")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(20, 20, 20, 20)
        panel_layout.setSpacing(16)
        layout.addWidget(panel, stretch=1)

        ref_header = QLabel("共同参考范文")
        ref_header.setObjectName("SectionHeader")
        panel_layout.addWidget(ref_header)

        ref_text = QTextEdit()
        ref_text.setReadOnly(True)
        ref_text.setStyleSheet("font-size: 14px; line-height: 1.6;")
        panel_layout.addWidget(ref_text, stretch=1)
        self.reference_text = ref_text

        input_header = QLabel("倒计时结束后开始输入，与对手比拼速度与准确度")
        input_header.setObjectName("SectionHeader")
        panel_layout.addWidget(input_header)

        user_text = QTextEdit()
        user_text.setPlaceholderText("请在此处输入您的文本，系统实时标色反馈")
        user_text.setStyleSheet("font-size: 14px; line-height: 1.6;")
        user_text.setReadOnly(True)
        user_text.textChanged.connect(self._on_text_change)
        panel_layout.addWidget(user_text, stretch=1)
        self.user_text = user_text

        status = QLabel("速度: 0.0 词/分钟 | 正确率: 100.0%")
        status.setObjectName("StatusLabel")
        layout.addWidget(status)
        self.status_label = status

        result_label = QLabel("")
        result_label.setAlignment(Qt.AlignCenter)
        result_label.setStyleSheet("font-size: 16px; font-weight: 700;")
        layout.addWidget(result_label)
        self.result_label = result_label

    def _render_reference(self) -> None:
        if self.reference_text is None:
            return
        self.reference_text.setPlainText(self.essay_content)

    def _start_countdown(self) -> None:
        self.countdown_timer = QTimer(self)
        self.countdown_timer.timeout.connect(self._tick_countdown)
        self.countdown_timer.start(1000)

    def _tick_countdown(self) -> None:
        if self.countdown_value > 0:
            if self.countdown_label is not None:
                self.countdown_label.setText(f"挑战将在 {self.countdown_value} 秒后开始")
            self.countdown_value -= 1
        else:
            self.countdown_timer.stop()
            if self.countdown_label is not None:
                self.countdown_label.setText("挑战开始！")
            if self.user_text is not None:
                self.user_text.setReadOnly(False)
                self.user_text.setFocus()
            self.stats.reset()

    def _on_text_change(self) -> None:
        if self.user_text is None or self.user_text.isReadOnly():
            return
        typed = self.user_text.toPlainText()
        target = self.essay_content

        self._highlight_text(typed, target)

        correct_chars = 0
        compare_len = min(len(typed), len(target))
        for idx in range(compare_len):
            if typed[idx] == target[idx]:
                correct_chars += 1

        self.stats.correct_letters = correct_chars
        self.stats.total_letters = len(typed)

        if self.status_label is not None:
            self.status_label.setText(
                f"速度: {self.stats.words_per_minute:.1f} 词/分钟 | 正确率: {self.stats.accuracy * 100:.1f}%"
            )

        if target and typed == target and not self.submitted:
            self.submitted = True
            self.stats.register_completion(len(target))
            if self.status_label is not None:
                self.status_label.setText(
                    f"速度: {self.stats.words_per_minute:.1f} 词/分钟 | 正确率: {self.stats.accuracy * 100:.1f}%"
                )
            if self.user_text is not None:
                self.user_text.setReadOnly(True)
            self.client.submit_result(self.challenge_id, self.stats.accuracy, self.stats.words_per_minute)
            if self.result_label is not None:
                self.result_label.setText("成绩已提交，等待对手完成...")
                self.result_label.setStyleSheet("color: #1a73e8;")

    def _highlight_text(self, typed: str, target: str) -> None:
        if self.user_text is None:
            return
        cursor_backup = self.user_text.textCursor()

        doc = self.user_text.document()
        default_format = QTextCharFormat()
        default_format.setForeground(QColor("#1f2933"))

        cursor = QTextCursor(doc)
        cursor.select(QTextCursor.Document)
        cursor.setCharFormat(default_format)

        correct_format = QTextCharFormat()
        correct_format.setForeground(QColor("#16a34a"))
        incorrect_format = QTextCharFormat()
        incorrect_format.setForeground(QColor("#dc2626"))

        compare_len = min(len(typed), len(target))

        for idx in range(compare_len):
            fmt = correct_format if typed[idx] == target[idx] else incorrect_format
            char_cursor = QTextCursor(doc)
            char_cursor.setPosition(idx)
            char_cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor)
            char_cursor.setCharFormat(fmt)

        for idx in range(compare_len, len(typed)):
            char_cursor = QTextCursor(doc)
            char_cursor.setPosition(idx)
            char_cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor)
            char_cursor.setCharFormat(incorrect_format)

        self.user_text.setTextCursor(cursor_backup)

    def show_result(self, winner: Optional[str], results: dict, my_id: Optional[str]) -> None:
        if self.result_label is None:
            return
        if winner is None:
            text = "本次挑战平局，双方实力旗鼓相当。"
            color = "#475569"
        elif winner == my_id:
            text = "恭喜您获胜！"
            color = "#16a34a"
        else:
            text = "对方获胜，再接再厉！"
            color = "#dc2626"
        details = json.dumps(results, ensure_ascii=False, indent=2)
        self.result_label.setText(text)
        self.result_label.setStyleSheet(f"color: {color};")
        QMessageBox.information(self, "挑战结果", f"{text}\n详细数据:\n{details}")

    def closeEvent(self, event) -> None:  # type: ignore[override]
        if hasattr(self, "countdown_timer") and self.countdown_timer.isActive():
            self.countdown_timer.stop()
        super().closeEvent(event)
