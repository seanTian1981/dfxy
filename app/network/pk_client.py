from __future__ import annotations

import json
import socket
import threading
from typing import Callable, Tuple

from app.network.pk_server import PK_PORT

MessageHandler = Callable[[dict], None]


class PkClient:
    def __init__(self, on_message: MessageHandler, server_addr: Tuple[str, int] = ("127.0.0.1", PK_PORT)) -> None:
        self.server_addr = server_addr
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("0.0.0.0", 0))
        self.on_message = on_message
        self.running = threading.Event()
        self.running.set()
        self.listener = threading.Thread(target=self._listen, daemon=True)
        self.listener.start()
        self.student_id: str | None = None
        self.name: str | None = None

    def _listen(self) -> None:
        while self.running.is_set():
            try:
                data, _ = self.sock.recvfrom(16384)
            except OSError:
                break
            try:
                payload = json.loads(data.decode("utf-8"))
            except json.JSONDecodeError:
                continue
            self.on_message(payload)

    def close(self) -> None:
        self.running.clear()
        self.sock.close()

    def register(self, student_id: str, name: str) -> None:
        self.student_id = student_id
        self.name = name
        payload = {
            "type": "register",
            "student_id": student_id,
            "name": name,
        }
        self._send(payload)

    def deregister(self) -> None:
        if not self.student_id:
            return
        payload = {"type": "deregister", "student_id": self.student_id}
        self._send(payload)

    def request_challenge(self, target_id: str) -> None:
        if not self.student_id:
            return
        payload = {
            "type": "challenge_request",
            "student_id": self.student_id,
            "target_id": target_id,
        }
        self._send(payload)

    def respond_challenge(self, challenger_id: str, accepted: bool) -> None:
        if not self.student_id:
            return
        payload = {
            "type": "challenge_response",
            "student_id": self.student_id,
            "challenger_id": challenger_id,
            "accepted": accepted,
        }
        self._send(payload)

    def submit_result(self, challenge_id: str, accuracy: float, speed: float) -> None:
        if not self.student_id:
            return
        payload = {
            "type": "result",
            "challenge_id": challenge_id,
            "student_id": self.student_id,
            "accuracy": accuracy,
            "speed": speed,
        }
        self._send(payload)

    def send_progress(self, challenge_id: str, accuracy: float, speed: float, progress: float) -> None:
        if not self.student_id:
            return
        payload = {
            "type": "progress",
            "challenge_id": challenge_id,
            "student_id": self.student_id,
            "accuracy": accuracy,
            "speed": speed,
            "progress": progress,
        }
        self._send(payload)

    def _send(self, payload: dict) -> None:
        raw = json.dumps(payload).encode("utf-8")
        self.sock.sendto(raw, self.server_addr)
