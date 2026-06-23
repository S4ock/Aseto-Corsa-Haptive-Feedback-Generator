"""Hybrid runtime mixer: stable continuous effects plus short event overlays."""
from __future__ import annotations

import math
import time


ROUGH_SURFACES = {"rough", "rumble", "gravel", "dirt", "grass", "rock", "mud", "sand", "cobblestone", "ridged"}


class RuntimeHapticMixer:
    def __init__(self, config: dict):
        self.config = config.get("runtime_mixer", config)
        self.left = 0.0
        self.right = 0.0
        self.last_time = time.monotonic()
        self.collision_until = 0.0

    def apply(self, telemetry: dict, prediction: dict, now: float | None = None) -> dict:
        now = time.monotonic() if now is None else now
        dt = max(.001, min(.25, now - self.last_time))
        self.last_time = now
        result = dict(prediction)
        if not self.config.get("enabled", True):
            return result
        speed = max(0.0, float(telemetry.get("speed_kmh", 0.0) or 0.0))
        rpm_ratio = _ratio(telemetry.get("rpm", 0.0), telemetry.get("max_rpm", 1.0))
        slips = [abs(float(telemetry.get(name, 0.0) or 0.0)) for name in ("wheel_slip_fl", "wheel_slip_fr", "wheel_slip_rl", "wheel_slip_rr")]
        max_slip = min(1.0, max(slips))
        surface = str(telemetry.get("surface_type", "unknown")).lower()
        rough = surface in ROUGH_SURFACES or not bool(telemetry.get("on_track", True))
        if float(telemetry.get("collision_intensity", 0.0) or 0.0) > 0:
            self.collision_until = now + float(self.config.get("collision_duration_seconds", .35))
        engine = max(0.0, rpm_ratio - .35) / .65 * float(self.config.get("engine_gain", .18))
        moving_floor = float(self.config.get("moving_vibration_floor", .04)) if speed > 5 else 0.0
        road = float(self.config.get("rough_surface_gain", .48)) if rough else 0.0
        pulse = .5 + .5 * math.sin(2 * math.pi * float(self.config.get("wheel_pulse_hz", 12.0)) * now)
        slip_layer = max(0.0, max_slip - .12) / .88 * float(self.config.get("wheel_slip_gain", .38)) * pulse
        collision = float(self.config.get("collision_gain", 1.0)) if now < self.collision_until else 0.0
        target_left = max(_value(prediction, "vibration_left"), engine + moving_floor, road, slip_layer, collision)
        target_right = max(_value(prediction, "vibration_right"), engine + moving_floor, road, slip_layer, collision)
        self.left = _envelope(self.left, target_left, dt, self.config)
        self.right = _envelope(self.right, target_right, dt, self.config)
        result["vibration_left"] = self.left
        result["vibration_right"] = self.right
        result["vibration_frequency"] = max(_value(prediction, "vibration_frequency"), rpm_ratio)
        if collision:
            result["haptic_event"] = "collision"
        elif rough:
            result["haptic_event"] = "off_track"
        elif max_slip > .35:
            result["haptic_event"] = "wheel_slip"
        return result


def _value(values: dict, name: str) -> float:
    try:
        return max(0.0, min(1.0, float(values.get(name, 0.0))))
    except (TypeError, ValueError):
        return 0.0


def _ratio(value, maximum) -> float:
    try:
        return max(0.0, min(1.0, float(value) / max(float(maximum), 1.0)))
    except (TypeError, ValueError):
        return 0.0


def _envelope(current: float, target: float, dt: float, config: dict) -> float:
    milliseconds = float(config.get("attack_ms", 40) if target > current else config.get("release_ms", 200))
    alpha = min(1.0, dt / max(.001, milliseconds / 1000.0))
    return max(0.0, min(1.0, current + (target - current) * alpha))
