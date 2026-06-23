"""Read-only Forza Horizon 5 Data Out endpoint.

For production binary Data Out parsing, pin the public packet version in config
and add offsets verified against that version. This intentionally refuses to infer
fields from unknown bytes and never reads game processes or memory.
"""
from __future__ import annotations

import json
import socket

from .base import TelemetryAdapter
from .normalizer import normalize


class ForzaHorizon5UdpAdapter(TelemetryAdapter):
    game = "forza_horizon_5"

    def connect(self) -> None:
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.settimeout(1.0)
        self.socket.bind((self.config.get("host", "127.0.0.1"), int(self.config.get("port", 5300))))

    def read_packet(self) -> dict | None:
        try:
            payload, _ = self.socket.recvfrom(65535)
        except socket.timeout:
            return None
        try:
            return json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return {"raw_packet_hex": payload.hex(), "packet_format": "unsupported_binary"}

    def normalize_packet(self, packet: dict) -> dict:
        return normalize(packet, self.game, self.session_id)

    def close(self) -> None:
        getattr(self, "socket", None) and self.socket.close()
