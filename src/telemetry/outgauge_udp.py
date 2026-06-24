"""Read-only OutGauge UDP telemetry used by BeamNG.drive and Live for Speed."""
from __future__ import annotations

import socket
import struct
from typing import Any

from .base import TelemetryAdapter
from .normalizer import normalize


# Documented OutGauge packet: time, car, flags, gear, player, 7 floats,
# dashboard lights, three input floats, and two display fields.
OUTGAUGE = struct.Struct("<I4sHBB7f2I3f16s16s")


class OutGaugeUdpAdapter(TelemetryAdapter):
    game = "outgauge"

    def connect(self) -> None:
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.settimeout(1.0)
        self.socket.bind((self.config.get("host", "127.0.0.1"), int(self.config.get("port", 4444))))

    def read_packet(self) -> dict[str, Any] | None:
        try:
            payload, _ = self.socket.recvfrom(512)
        except socket.timeout:
            return None
        if len(payload) != OUTGAUGE.size:
            print(f"Ignoring malformed OutGauge packet ({len(payload)} bytes; expected {OUTGAUGE.size}).")
            return None
        values = OUTGAUGE.unpack(payload)
        time_ms, car, _flags, gear, _player, speed, rpm, _turbo, _engine_temp, fuel, _oil_pressure, _oil_temp, _dash, _show, throttle, brake, clutch, _display1, _display2 = values
        return {
            "timestamp": time_ms / 1000.0,
            "car": car.rstrip(b"\0").decode("ascii", errors="replace"),
            "speed_kmh": max(0.0, speed * 3.6),
            "rpm": max(0.0, rpm),
            "max_rpm": float(self.config.get("max_rpm", 9000)),
            "gear": int(gear) - 1,
            "throttle": throttle,
            "brake": brake,
            "clutch": clutch,
        }

    def normalize_packet(self, packet: dict[str, Any]) -> dict[str, Any]:
        return normalize(packet, self.game, self.session_id)

    def close(self) -> None:
        getattr(self, "socket", None) and self.socket.close()


class BeamNGDriveOutGaugeAdapter(OutGaugeUdpAdapter):
    game = "beamng_drive"


class LiveForSpeedOutGaugeAdapter(OutGaugeUdpAdapter):
    game = "live_for_speed"
