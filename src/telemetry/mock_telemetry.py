"""Deterministic fake telemetry for the complete offline demo pipeline."""
from __future__ import annotations

import math
import random
import time

from .base import TelemetryAdapter
from .normalizer import normalize


class MockTelemetryAdapter(TelemetryAdapter):
    game = "mock"

    def __init__(self, config: dict, session_id: str):
        super().__init__(config, session_id)
        self.rate = float(config.get("sample_rate_hz", 30))
        self.rng = random.Random(config.get("seed", 25))
        self.index = 0
        self.connected = False

    def connect(self) -> None:
        self.connected = True

    def read_packet(self) -> dict | None:
        if not self.connected:
            return None
        t = self.index / self.rate
        phase = self.index % 300
        throttle = 0.85 if phase < 100 else 0.25 if phase < 180 else 0.65
        brake = 0.0 if phase < 130 else min(1.0, (phase - 130) / 35) if phase < 180 else 0.0
        steering = math.sin(t * 1.8) * (0.75 if 40 < phase < 180 else 0.25)
        rear_slip = 0.62 if 65 < phase < 95 else 0.12 + abs(steering) * 0.12
        off_track = 220 < phase < 250
        collision = 0.9 if phase == 255 else 0.0
        speed = max(0, 80 + 55 * math.sin(t / 3) - brake * 50)
        self.index += 1
        return {
            "timestamp": time.time(), "speed_kmh": speed, "rpm": 3500 + throttle * 7000,
            "max_rpm": 11500, "gear": 4, "throttle": throttle, "brake": brake,
            "steering": steering, "accel_x": throttle * 3 - brake * 5,
            "accel_y": steering * speed / 35, "accel_z": 9.81,
            "velocity_x": speed / 3.6, "wheel_slip_fl": rear_slip * 0.6,
            "wheel_slip_fr": rear_slip * 0.6, "wheel_slip_rl": rear_slip,
            "wheel_slip_rr": rear_slip + self.rng.uniform(-0.03, 0.03),
            "surface_type": "rough" if off_track else "asphalt", "on_track": not off_track,
            "collision_intensity": collision, "abs_active": brake > 0.8,
            "traction_control_active": rear_slip > 0.45,
        }

    def normalize_packet(self, packet: dict) -> dict:
        return normalize(packet, self.game, self.session_id)

    def close(self) -> None:
        self.connected = False
