"""Original Assetto Corsa's documented, read-only shared-memory telemetry.

Assetto Corsa publishes ``Local\\acpmf_physics`` for telemetry consumers. This
adapter opens only that named, documented mapping with read permission; it does
not scan memory, inspect processes, or write to the game.
"""
from __future__ import annotations

import ctypes
import struct
import time
from typing import Any

from .base import TelemetryAdapter
from .normalizer import normalize


# Includes the stable leading physics fields plus the documented carDamage[5].
PHYSICS_MIN_SIZE = 244
FILE_MAP_READ = 0x0004


class AssettoCorsaAdapter(TelemetryAdapter):
    """Read the stable leading fields of Assetto Corsa's SPageFilePhysics."""

    game = "assetto_corsa"

    def __init__(self, config: dict[str, Any], session_id: str):
        super().__init__(config, session_id)
        self.last_packet_id: int | None = None
        self.max_rpm = float(config.get("max_rpm", 9000))
        self.max_steering_angle = max(.01, float(config.get("max_steering_angle_rad", .6)))
        self.slip_scale = max(.01, float(config.get("wheel_slip_scale", 1.0)))
        self.damage_delta_threshold = max(.0001, float(config.get("collision_damage_delta_threshold", .01)))
        self.previous_damage: tuple[float, ...] | None = None
        self._collision_packets_remaining = 0
        self._collision_strength = 0.0

    def connect(self) -> None:
        if not self.config.get("enabled", True):
            raise RuntimeError("Assetto Corsa telemetry is disabled in config/games.yaml.")
        if not hasattr(ctypes, "windll"):
            raise RuntimeError("Assetto Corsa shared-memory telemetry is supported on Windows only.")
        self.kernel32 = ctypes.windll.kernel32
        self.kernel32.OpenFileMappingW.argtypes = [ctypes.c_uint32, ctypes.c_bool, ctypes.c_wchar_p]
        self.kernel32.OpenFileMappingW.restype = ctypes.c_void_p
        self.kernel32.MapViewOfFile.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_size_t]
        self.kernel32.MapViewOfFile.restype = ctypes.c_void_p
        self.kernel32.UnmapViewOfFile.argtypes = [ctypes.c_void_p]
        self.kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
        mapping_name = self.config.get("physics_map", r"Local\acpmf_physics")
        self.mapping_handle = self.kernel32.OpenFileMappingW(FILE_MAP_READ, False, mapping_name)
        if not self.mapping_handle:
            raise RuntimeError("Assetto Corsa telemetry mapping was not found. Start an offline session first, then run the recorder.")
        self.view = self.kernel32.MapViewOfFile(self.mapping_handle, FILE_MAP_READ, 0, 0, PHYSICS_MIN_SIZE)
        if not self.view:
            self.kernel32.CloseHandle(self.mapping_handle)
            raise RuntimeError("Could not open the Assetto Corsa telemetry view as read-only.")

    def read_packet(self) -> dict[str, Any] | None:
        data = ctypes.string_at(self.view, PHYSICS_MIN_SIZE)
        packet_id = struct.unpack_from("<i", data, 0)[0]
        if packet_id == self.last_packet_id:
            return None
        self.last_packet_id = packet_id
        gas, brake, _fuel = struct.unpack_from("<3f", data, 4)
        gear, rpm = struct.unpack_from("<2i", data, 16)
        steering, speed = struct.unpack_from("<2f", data, 24)
        velocity = struct.unpack_from("<3f", data, 32)
        acceleration_g = struct.unpack_from("<3f", data, 44)
        wheel_slip = struct.unpack_from("<4f", data, 56)
        tyre_core_temperature = struct.unpack_from("<4f", data, 152)
        # SPageFilePhysics: camber[4], suspensionTravel[4], drs/tc, heading/pitch/roll/cgHeight, carDamage[5].
        car_damage = struct.unpack_from("<5f", data, 224)
        damage_delta = 0.0 if self.previous_damage is None else sum(max(0.0, current - previous) for current, previous in zip(car_damage, self.previous_damage))
        self.previous_damage = car_damage
        if damage_delta >= self.damage_delta_threshold:
            self._collision_packets_remaining = 6
            self._collision_strength = min(1.0, damage_delta / self.damage_delta_threshold)
        collision_intensity = self._collision_strength if self._collision_packets_remaining else 0.0
        if self._collision_packets_remaining:
            self._collision_packets_remaining -= 1
        return {
            "timestamp": time.time(), "speed_kmh": speed, "rpm": rpm, "max_rpm": self.max_rpm,
            "gear": gear, "throttle": gas, "brake": brake,
            "steering": steering / self.max_steering_angle,
            "accel_x": acceleration_g[0] * 9.81, "accel_y": acceleration_g[1] * 9.81, "accel_z": acceleration_g[2] * 9.81,
            "velocity_x": velocity[0], "velocity_y": velocity[1], "velocity_z": velocity[2],
            "wheel_slip_fl": _slip(wheel_slip[0], self.slip_scale), "wheel_slip_fr": _slip(wheel_slip[1], self.slip_scale),
            "wheel_slip_rl": _slip(wheel_slip[2], self.slip_scale), "wheel_slip_rr": _slip(wheel_slip[3], self.slip_scale),
            "tire_temp_fl": tyre_core_temperature[0], "tire_temp_fr": tyre_core_temperature[1],
            "tire_temp_rl": tyre_core_temperature[2], "tire_temp_rr": tyre_core_temperature[3],
            "surface_type": "unknown", "on_track": True,
            "collision_intensity": collision_intensity,
        }

    def normalize_packet(self, packet: dict[str, Any]) -> dict[str, Any]:
        return normalize(packet, self.game, self.session_id)

    def close(self) -> None:
        view = getattr(self, "view", None)
        handle = getattr(self, "mapping_handle", None)
        if view:
            self.kernel32.UnmapViewOfFile(view)
            self.view = None
        if handle:
            self.kernel32.CloseHandle(handle)
            self.mapping_handle = None


def _slip(value: float, scale: float) -> float:
    return min(1.0, abs(float(value)) / scale)
