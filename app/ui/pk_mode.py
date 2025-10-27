from __future__ import annotations

import json
import queue
import re
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Dict, List, Optional

from app.core.stats import EssayStats
from app.network.pk_client import PkClient
from app.network.pk_server import PkServer, PK_PORT

BANNED_KEYWORDS = {"傻", "笨", "蠢", "操", "妈", "垃圾", "滚", "死"}


class PkModeFrame(ttk.Frame):
    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master)
        self.server: Optional[PkServer] = None
        self.client: Optional[PkClient] = None
        self.message_queue: "queue.Queue[dict]" = queue.Queue()
        self.users: Dict[str, str] = {}
        self.student_id_var = tk.StringVar()
        self.name_var = tk.StringVar()
        self.status_var = tk.StringVar(value="未连接")
        self.challenge_window: Optional[ChallengeWindow] = None
        self.current_challenge_id: Optional[str] = None

        self._ensure_server()
        self._build_ui()
        self.after(200, self._process_messages)

    def _ensure_server(self) -> None:
        try:
            server = PkServer()
            server.start()
            self.server = server
            self.status_var.set(f"已启动本地对战服务器 (端口 {PK_PORT})")
        except OSError:
            # 端口已被占用，认为已有服务器存在
            self.server = None
            self.status_var.set(f"检测到已有服务器，准备连接 (端口 {PK_PORT})")

    def _build_ui(self) -> None:
        form_frame = ttk.Frame(self)
        form_frame.pack(fill=tk.X, padx=12, pady=8)

        ttk.Label(form_frame, text="学号 (8位数字):").grid(row=0, column=0, sticky=tk.W)
        ttk.Entry(form_frame, textvariable=self.student_id_var, width=15).grid(row=0, column=1, padx=(6, 12))

        ttk.Label(form_frame, text="姓名 (2-4个中文字符):").grid(row=0, column=2, sticky=tk.W)
        ttk.Entry(form_frame, textvariable=self.name_var, width=12).grid(row=0, column=3, padx=(6, 12))

        self.connect_button = ttk.Button(form_frame, text="连接", command=self._on_connect)
        self.connect_button.grid(row=0, column=4, padx=(4, 0))

        self.disconnect_button = ttk.Button(form_frame, text="断开", command=self._on_disconnect, state=tk.DISABLED)
        self.disconnect_button.grid(row=0, column=5, padx=(6, 0))

        self.status_label = ttk.Label(self, textvariable=self.status_var, anchor=tk.W)
        self.status_label.pack(fill=tk.X, padx=12, pady=4)

        list_frame = ttk.Frame(self)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        ttk.Label(list_frame, text="在线用户 (双击挑战)", font=("Helvetica", 12, "bold")).pack(anchor=tk.W)
        self.user_listbox = tk.Listbox(list_frame, height=12)
        self.user_listbox.pack(fill=tk.BOTH, expand=True, pady=(6, 0))
        self.user_listbox.bind("<Double-Button-1>", self._on_user_double_click)

    def _on_connect(self) -> None:
        student_id = self.student_id_var.get().strip()
        name = self.name_var.get().strip()

        if not re.fullmatch(r"\d{8}", student_id):
            messagebox.showerror("输入错误", "学号必须是8位数字")
            return
        if not (2 <= len(name) <= 4) or not all("\u4e00" <= ch <= "\u9fff" for ch in name):
            messagebox.showerror("输入错误", "姓名必须为2-4个中文字符")
            return
        if any(keyword in name for keyword in BANNED_KEYWORDS):
            messagebox.showerror("输入错误", "请勿使用不文明的称呼")
            return

        if self.client is None:
            self.client = PkClient(on_message=self.message_queue.put)
        self.client.register(student_id, name)
        self.connect_button.config(state=tk.DISABLED)
        self.disconnect_button.config(state=tk.NORMAL)
        self.status_var.set("已连接, 正在等待用户列表...")

    def _on_disconnect(self) -> None:
        if self.client:
            self.client.deregister()
            self.client.close()
            self.client = None
        self.users.clear()
        self._refresh_user_list()
        self.connect_button.config(state=tk.NORMAL)
        self.disconnect_button.config(state=tk.DISABLED)
        self.status_var.set("已断开连接")

    def _process_messages(self) -> None:
        try:
            while True:
                message = self.message_queue.get_nowait()
                self._handle_message(message)
        except queue.Empty:
            pass
        finally:
            self.after(200, self._process_messages)

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
        self.status_var.set(f"当前在线 {len(users)} 人")

    def _refresh_user_list(self) -> None:
        self.user_listbox.delete(0, tk.END)
        for student_id, name in self.users.items():
            self.user_listbox.insert(tk.END, f"{name} ({student_id})")

    def _on_user_double_click(self, _event: tk.Event) -> None:
        selection = self.user_listbox.curselection()
        if not selection or self.client is None:
            return
        index = selection[0]
        student_id = list(self.users.keys())[index]
        self.client.request_challenge(student_id)
        self.status_var.set(f"已向 {self.users[student_id]} 发起挑战，等待回应...")

    def _handle_challenge_request(self, message: dict) -> None:
        challenger = message.get("from", {})
        challenger_name = challenger.get("name", "未知")
        challenger_id = challenger.get("student_id", "")
        if not challenger_id or self.client is None:
            return
        accept = messagebox.askyesno(
            "收到挑战",
            f"{challenger_name} 向您发起挑战，是否接受?",
        )
        self.client.respond_challenge(challenger_id, accept)
        if accept:
            self.status_var.set(f"已接受 {challenger_name} 的挑战，准备开始...")
        else:
            messagebox.showinfo("提示", "您已拒绝对方的挑战")
            self.status_var.set(f"已拒绝 {challenger_name} 的挑战")

    def _handle_challenge_response(self, message: dict) -> None:
        accepted = message.get("accepted", False)
        responder = message.get("from", {})
        responder_name = responder.get("name", "对方")
        if accepted:
            self.status_var.set(f"{responder_name} 接受了您的挑战，准备中...")
        else:
            messagebox.showinfo("提示", "对方不接受您的挑战")
            self.status_var.set(f"{responder_name} 拒绝了挑战")

    def _handle_start_challenge(self, message: dict) -> None:
        if self.client is None:
            return
        challenge_id = message.get("challenge_id")
        essay = message.get("essay", {})
        self.current_challenge_id = challenge_id
        if self.challenge_window and self.challenge_window.winfo_exists():
            self.challenge_window.destroy()
        self.challenge_window = ChallengeWindow(
            parent=self,
            client=self.client,
            challenge_id=challenge_id,
            essay_title=essay.get("title", "PK 练习"),
            essay_content=essay.get("content", ""),
        )
        self.status_var.set("挑战开始，祝您好运！")

    def _handle_challenge_result(self, message: dict) -> None:
        challenge_id = message.get("challenge_id")
        if challenge_id != self.current_challenge_id:
            return
        winner = message.get("winner")
        results = message.get("results", {})
        my_id = self.client.student_id if self.client else None
        if self.challenge_window and self.challenge_window.winfo_exists():
            self.challenge_window.show_result(winner, results, my_id)
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
        messagebox.showinfo("挑战结果", text)

    def destroy(self) -> None:
        if self.client:
            self.client.deregister()
            self.client.close()
        if self.server:
            self.server.stop()
            self.server.join(timeout=1)
        super().destroy()


class ChallengeWindow(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Misc,
        client: PkClient,
        challenge_id: str,
        essay_title: str,
        essay_content: str,
    ) -> None:
        super().__init__(parent)
        self.client = client
        self.challenge_id = challenge_id
        self.essay_title = essay_title
        self.essay_content = essay_content.strip()
        self.stats = EssayStats()
        self.submitted = False
        self.countdown = 5
        self.result_label: Optional[ttk.Label] = None

        self.title("四六级作文 PK")
        self.geometry("760x520")
        self._build_ui()
        self._start_countdown()

    def _build_ui(self) -> None:
        ttk.Label(self, text=self.essay_title, font=("Helvetica", 18, "bold")).pack(pady=8)
        self.countdown_var = tk.StringVar(value="挑战将在 5 秒后开始")
        ttk.Label(self, textvariable=self.countdown_var, font=("Helvetica", 14)).pack()

        paned = ttk.Panedwindow(self, orient=tk.VERTICAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        reference_frame = ttk.Frame(paned)
        paned.add(reference_frame, weight=1)
        ttk.Label(reference_frame, text="共同参考范文", font=("Helvetica", 12, "bold")).pack(anchor=tk.W)
        self.reference_text = tk.Text(reference_frame, wrap=tk.WORD, height=10, state=tk.DISABLED)
        self.reference_text.pack(fill=tk.BOTH, expand=True, pady=(4, 8))
        self._render_reference()

        input_frame = ttk.Frame(paned)
        paned.add(input_frame, weight=1)
        ttk.Label(input_frame, text="请在倒计时结束后开始输入", font=("Helvetica", 12, "bold")).pack(anchor=tk.W)
        self.user_text = tk.Text(input_frame, wrap=tk.WORD, height=10, state=tk.DISABLED)
        self.user_text.pack(fill=tk.BOTH, expand=True, pady=(4, 8))
        self.user_text.tag_configure("correct", foreground="#2e8b57")
        self.user_text.tag_configure("incorrect", foreground="#b22222")
        self.user_text.bind("<KeyRelease>", self._on_text_change)

        self.status_var = tk.StringVar(value="速度: 0.0 词/分钟 | 正确率: 100.0%")
        ttk.Label(self, textvariable=self.status_var, anchor=tk.W).pack(fill=tk.X, padx=12, pady=(0, 8))
        self.result_label = ttk.Label(self, text="", anchor=tk.CENTER, font=("Helvetica", 14, "bold"))
        self.result_label.pack(fill=tk.X, padx=12, pady=(0, 8))

    def _render_reference(self) -> None:
        self.reference_text.configure(state=tk.NORMAL)
        self.reference_text.delete("1.0", tk.END)
        self.reference_text.insert("1.0", self.essay_content)
        self.reference_text.configure(state=tk.DISABLED)

    def _start_countdown(self) -> None:
        if self.countdown > 0:
            self.countdown_var.set(f"挑战将在 {self.countdown} 秒后开始")
            self.countdown -= 1
            self.after(1000, self._start_countdown)
        else:
            self.countdown_var.set("挑战开始！")
            self.stats.reset()
            self.user_text.configure(state=tk.NORMAL)
            self.user_text.focus_set()

    def _on_text_change(self, _event: tk.Event | None = None) -> None:
        if self.user_text.cget("state") == tk.DISABLED:
            return
        typed = self.user_text.get("1.0", tk.END).rstrip()
        target = self.essay_content

        self.user_text.tag_remove("correct", "1.0", tk.END)
        self.user_text.tag_remove("incorrect", "1.0", tk.END)

        correct_chars = 0
        compare_len = min(len(typed), len(target))

        for idx in range(compare_len):
            start = f"1.0+{idx}c"
            end = f"1.0+{idx + 1}c"
            if typed[idx] == target[idx]:
                self.user_text.tag_add("correct", start, end)
                correct_chars += 1
            else:
                self.user_text.tag_add("incorrect", start, end)

        for idx in range(compare_len, len(typed)):
            start = f"1.0+{idx}c"
            end = f"1.0+{idx + 1}c"
            self.user_text.tag_add("incorrect", start, end)

        self.stats.correct_letters = correct_chars
        self.stats.total_letters = len(typed)
        self.status_var.set(
            f"速度: {self.stats.words_per_minute:.1f} 词/分钟 | 正确率: {self.stats.accuracy * 100:.1f}%"
        )

        if typed == target and not self.submitted and target:
            self.submitted = True
            self.user_text.configure(state=tk.DISABLED)
            self.stats.register_completion(len(target))
            self.status_var.set(
                f"速度: {self.stats.words_per_minute:.1f} 词/分钟 | 正确率: {self.stats.accuracy * 100:.1f}%"
            )
            self.client.submit_result(
                self.challenge_id, self.stats.accuracy, self.stats.words_per_minute
            )
            self.result_label.config(text="成绩已提交，等待对手完成...", foreground="#1e90ff")

    def show_result(self, winner: Optional[str], results: dict, my_id: Optional[str]) -> None:
        if winner is None:
            text = "本次挑战平局，双方实力旗鼓相当。"
            color = "#444444"
        elif winner == my_id:
            text = "恭喜您获胜！"
            color = "#2e8b57"
        else:
            text = "对方获胜，再接再厉！"
            color = "#b22222"
        details = json.dumps(results, ensure_ascii=False, indent=2)
        self.result_label.config(text=text, foreground=color)
        messagebox.showinfo("挑战结果", f"{text}\n详细数据:\n{details}")
