from __future__ import annotations

import json
import random
import socket
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, Tuple

from app.core.data_loader import load_essays

PK_PORT = 8270


@dataclass
class ClientInfo:
    student_id: str
    name: str
    addr: Tuple[str, int]
    last_seen: float = field(default_factory=time.time)


@dataclass
class ChallengeInfo:
    challenger: ClientInfo
    opponent: ClientInfo
    essay: dict
    results: Dict[str, dict] = field(default_factory=dict)


class PkServer(threading.Thread):
    def __init__(self, host: str = "0.0.0.0", port: int = PK_PORT) -> None:
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.host, self.port))
        self.clients: Dict[str, ClientInfo] = {}
        self.challenges: Dict[str, ChallengeInfo] = {}
        self.running = threading.Event()
        self.running.set()
        self.essays = load_essays()

    def run(self) -> None:
        while self.running.is_set():
            try:
                data, addr = self.sock.recvfrom(16384)
            except OSError:
                break
            try:
                payload = json.loads(data.decode("utf-8"))
            except json.JSONDecodeError:
                continue
            self._handle_message(payload, addr)

    def stop(self) -> None:
        self.running.clear()
        self.sock.close()

    def _handle_message(self, message: dict, addr: Tuple[str, int]) -> None:
        msg_type = message.get("type")
        if msg_type == "register":
            self._handle_register(message, addr)
        elif msg_type == "deregister":
            student_id = message.get("student_id")
            if student_id and student_id in self.clients:
                self.clients.pop(student_id)
                self._broadcast_user_list()
        elif msg_type == "challenge_request":
            self._handle_challenge_request(message)
        elif msg_type == "challenge_response":
            self._handle_challenge_response(message)
        elif msg_type == "progress":
            self._handle_progress(message)
        elif msg_type == "result":
            self._handle_result(message)

    def _handle_register(self, message: dict, addr: Tuple[str, int]) -> None:
        student_id = str(message.get("student_id", "")).strip()
        name = str(message.get("name", "")).strip()
        if not student_id or not name:
            return
        info = ClientInfo(student_id=student_id, name=name, addr=addr)
        self.clients[student_id] = info
        self._broadcast_user_list()

    def _broadcast_user_list(self) -> None:
        user_list = [
            {
                "student_id": client.student_id,
                "name": client.name,
                "ip": client.addr[0],
            }
            for client in self.clients.values()
        ]
        payload = json.dumps({"type": "user_list", "users": user_list}).encode("utf-8")
        for client in self.clients.values():
            self.sock.sendto(payload, client.addr)

    def _handle_challenge_request(self, message: dict) -> None:
        target_id = message.get("target_id")
        if target_id not in self.clients:
            return
        challenger_id = message.get("student_id")
        challenger = self.clients.get(challenger_id)
        opponent = self.clients[target_id]
        if challenger is None:
            return
        payload = {
            "type": "challenge_request",
            "from": {
                "student_id": challenger.student_id,
                "name": challenger.name,
                "ip": challenger.addr[0],
            },
        }
        self.sock.sendto(json.dumps(payload).encode("utf-8"), opponent.addr)

    def _handle_challenge_response(self, message: dict) -> None:
        accepted = bool(message.get("accepted"))
        challenger_id = message.get("challenger_id")
        responder_id = message.get("student_id")

        challenger = self.clients.get(challenger_id)
        responder = self.clients.get(responder_id)
        if challenger is None or responder is None:
            return

        response_payload = {
            "type": "challenge_response",
            "accepted": accepted,
            "from": {
                "student_id": responder.student_id,
                "name": responder.name,
                "ip": responder.addr[0],
            },
        }
        self.sock.sendto(json.dumps(response_payload).encode("utf-8"), challenger.addr)

        if accepted:
            essay = random.choice(self.essays)
            challenge_id = f"{challenger.student_id}-{responder.student_id}-{int(time.time()*1000)}"
            challenge_info = ChallengeInfo(
                challenger=challenger,
                opponent=responder,
                essay={
                    "title": essay.title,
                    "content": essay.content,
                },
            )
            self.challenges[challenge_id] = challenge_info
            start_payload = {
                "type": "start_challenge",
                "challenge_id": challenge_id,
                "essay": challenge_info.essay,
                "participants": [
                    {
                        "student_id": challenger.student_id,
                        "name": challenger.name,
                        "ip": challenger.addr[0],
                    },
                    {
                        "student_id": responder.student_id,
                        "name": responder.name,
                        "ip": responder.addr[0],
                    },
                ],
            }
            raw = json.dumps(start_payload).encode("utf-8")
            self.sock.sendto(raw, challenger.addr)
            self.sock.sendto(raw, responder.addr)

    def _handle_progress(self, message: dict) -> None:
        challenge_id = message.get("challenge_id")
        student_id = message.get("student_id")
        if not challenge_id or not student_id:
            return
        challenge = self.challenges.get(challenge_id)
        if challenge is None:
            return
        if student_id not in (
            challenge.challenger.student_id,
            challenge.opponent.student_id,
        ):
            return
        def _to_float(value: object, default: float = 0.0) -> float:
            try:
                return float(value)
            except (TypeError, ValueError):
                return default

        progress_value = _to_float(message.get("progress", 0.0))
        progress_value = max(0.0, min(progress_value, 1.0))
        payload = {
            "type": "progress_update",
            "challenge_id": challenge_id,
            "student_id": student_id,
            "accuracy": _to_float(message.get("accuracy", 0.0)),
            "speed": _to_float(message.get("speed", 0.0)),
            "progress": progress_value,
        }
        raw = json.dumps(payload).encode("utf-8")
        self.sock.sendto(raw, challenge.challenger.addr)
        self.sock.sendto(raw, challenge.opponent.addr)

    def _handle_result(self, message: dict) -> None:
        challenge_id = message.get("challenge_id")
        student_id = message.get("student_id")
        if challenge_id not in self.challenges or student_id not in self.clients:
            return
        challenge = self.challenges[challenge_id]
        challenge.results[student_id] = {
            "accuracy": float(message.get("accuracy", 0.0)),
            "speed": float(message.get("speed", 0.0)),
        }
        if len(challenge.results) < 2:
            return
        self._evaluate_challenge(challenge_id)

    def _evaluate_challenge(self, challenge_id: str) -> None:
        challenge = self.challenges.pop(challenge_id, None)
        if challenge is None:
            return
        challenger_stats = challenge.results.get(challenge.challenger.student_id, {})
        opponent_stats = challenge.results.get(challenge.opponent.student_id, {})

        winner_id = self._select_winner(challenger_stats, opponent_stats, challenge)
        payload = {
            "type": "challenge_result",
            "challenge_id": challenge_id,
            "winner": winner_id,
            "results": challenge.results,
        }
        raw = json.dumps(payload).encode("utf-8")
        self.sock.sendto(raw, challenge.challenger.addr)
        self.sock.sendto(raw, challenge.opponent.addr)

    @staticmethod
    def _select_winner(challenger_stats: dict, opponent_stats: dict, challenge: ChallengeInfo) -> str | None:
        c_acc = challenger_stats.get("accuracy", 0.0)
        o_acc = opponent_stats.get("accuracy", 0.0)
        if abs(c_acc - o_acc) > 1e-6:
            return (
                challenge.challenger.student_id
                if c_acc > o_acc
                else challenge.opponent.student_id
            )
        c_speed = challenger_stats.get("speed", 0.0)
        o_speed = opponent_stats.get("speed", 0.0)
        if abs(c_speed - o_speed) > 1e-6:
            return (
                challenge.challenger.student_id
                if c_speed > o_speed
                else challenge.opponent.student_id
            )
        return None
