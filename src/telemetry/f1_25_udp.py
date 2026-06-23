"""Read-only decoder for the public F1 UDP car-telemetry packet.

The implementation intentionally reads only packet ID 6 (car telemetry) and
only its stable, documented fixed-width fields. Other packet IDs are ignored,
which prevents a configured 20 Hz send rate from being inflated by unrelated
session/motion/status packets. No process access or game-memory access exists.
"""
from __future__ import annotations

import socket
import struct
from typing import Any

from .base import TelemetryAdapter
from .normalizer import normalize


# Public F1 UDP header used by the 2026 format: 29 bytes, little-endian.
HEADER = struct.Struct("<HBBBBBQfIIBB")
# Stable portion of CarTelemetryData: 60 bytes per car, 22 car slots.
CAR_TELEMETRY = struct.Struct("<HfffBbHBBH4H4B4BH4f4B")
CAR_TELEMETRY_PACKET_ID = 6
EVENT_PACKET_ID = 3
EVENT_CODE_SIZE = 4
COLLISION_EVENT_CODE = b"COLL"
SURFACES = {
    0: "tarmac", 1: "rumble", 2: "concrete", 3: "rock", 4: "gravel",
    5: "mud", 6: "sand", 7: "grass", 8: "water", 9: "cobblestone",
    10: "metal", 11: "ridged",
}
ROUGH_SURFACES = {"rock", "gravel", "mud", "sand", "grass", "cobblestone", "ridged"}


class F125UdpAdapter(TelemetryAdapter):
    """Decode official F1 2026 UDP telemetry without modifying the game."""

    game = "f1_25"  # Retained as the project/game-split identifier from the original design.

    def __init__(self, config: dict[str, Any], session_id: str):
        super().__init__(config, session_id)
        self.expected_format = int(config.get("udp_format", 2026))
        self.max_rpm = float(config.get("max_rpm", 15000))
        self._format_warning_printed = False
        self._collision_packets_remaining = 0

    def connect(self) -> None:
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.settimeout(1.0)
        self.socket.bind((self.config.get("host", "127.0.0.1"), int(self.config.get("port", 20777))))

    def read_packet(self) -> dict[str, Any] | None:
        try:
            payload, _ = self.socket.recvfrom(65535)
        except socket.timeout:
            return None
        if len(payload) < HEADER.size:
            return None
        header = HEADER.unpack_from(payload)
        packet_format, _year, _major, _minor, _packet_version, packet_id, _session_uid, session_time, _frame, _overall_frame, player_index, _secondary_index = header
        if packet_format != self.expected_format:
            if not self._format_warning_printed:
                print(f"Ignoring F1 UDP format {packet_format}; config expects {self.expected_format}. Check Telemetry Settings.")
                self._format_warning_printed = True
            return None
        if packet_id == EVENT_PACKET_ID:
            self._read_event(payload, int(player_index))
            return None
        if packet_id != CAR_TELEMETRY_PACKET_ID:
            return None
        car_offset = HEADER.size + int(player_index) * CAR_TELEMETRY.size
        if player_index >= 22 or len(payload) < car_offset + CAR_TELEMETRY.size:
            print("Ignoring malformed F1 car telemetry packet.")
            return None
        values = CAR_TELEMETRY.unpack_from(payload, car_offset)
        speed, throttle, steering, brake, clutch, gear, rpm, _drs, _rev_percent, _rev_lights, *tail = values
        brake_temps = tail[0:4]
        tyre_surface_temps = tail[4:8]
        tyre_inner_temps = tail[8:12]
        _engine_temp = tail[12]
        _tyre_pressures = tail[13:17]
        surface_ids = tail[17:21]
        surface_names = [SURFACES.get(value, "unknown") for value in surface_ids]
        surface = next((name for name in surface_names if name in ROUGH_SURFACES), surface_names[0])
        collision_intensity = 1.0 if self._collision_packets_remaining else 0.0
        if self._collision_packets_remaining:
            self._collision_packets_remaining -= 1
        return {
            "timestamp": float(session_time),
            "speed_kmh": float(speed), "rpm": float(rpm), "max_rpm": self.max_rpm,
            "gear": int(gear), "throttle": float(throttle), "brake": float(brake),
            "clutch": float(clutch) / 100.0, "steering": float(steering),
            "tire_temp_fl": float(tyre_surface_temps[0]), "tire_temp_fr": float(tyre_surface_temps[1]),
            "tire_temp_rl": float(tyre_surface_temps[2]), "tire_temp_rr": float(tyre_surface_temps[3]),
            "brake_temp_fl": float(brake_temps[0]), "brake_temp_fr": float(brake_temps[1]),
            "brake_temp_rl": float(brake_temps[2]), "brake_temp_rr": float(brake_temps[3]),
            "tire_inner_temp_fl": float(tyre_inner_temps[0]), "tire_inner_temp_fr": float(tyre_inner_temps[1]),
            "tire_inner_temp_rl": float(tyre_inner_temps[2]), "tire_inner_temp_rr": float(tyre_inner_temps[3]),
            "surface_type": surface, "on_track": surface not in ROUGH_SURFACES,
            "collision_intensity": collision_intensity,
            "raw_packet_hex": payload.hex(), "packet_format": packet_format,
        }

    def _read_event(self, payload: bytes, player_index: int) -> None:
        """Handle only the official collision event, without inspecting other state."""
        event_offset = HEADER.size
        if len(payload) < event_offset + EVENT_CODE_SIZE:
            return
        if payload[event_offset:event_offset + EVENT_CODE_SIZE] != COLLISION_EVENT_CODE:
            return
        details_offset = event_offset + EVENT_CODE_SIZE
        if len(payload) < details_offset + 2:
            return
        vehicle_one, vehicle_two = payload[details_offset], payload[details_offset + 1]
        if player_index in (vehicle_one, vehicle_two):
            # At 20 Hz, six frames is a brief 300 ms event rather than a stuck vibration.
            self._collision_packets_remaining = 6

    def normalize_packet(self, packet: dict[str, Any]) -> dict[str, Any]:
        return normalize(packet, self.game, self.session_id)

    def close(self) -> None:
        getattr(self, "socket", None) and self.socket.close()
