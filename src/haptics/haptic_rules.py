"""Our own telemetry-derived labels; no commercial haptic data is captured."""
from __future__ import annotations

import math

from src.constants import HAPTIC_COLUMNS, SLIP_COLUMNS
from src.haptics.smoothing import FeedbackSmoother


def _clamp(value: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, number)) if math.isfinite(number) else 0.0


class HapticRuleEngine:
    def __init__(self, config: dict):
        self.config = config
        self.previous_brake = 0.0
        self.smoother = FeedbackSmoother(config.get("smoothing_factor", 0.35))

    def label(self, row: dict) -> dict:
        brake = _clamp(row.get("brake", 0.0))
        throttle = _clamp(row.get("throttle", 0.0))
        slips = [_clamp(row.get(column, 0.0)) for column in SLIP_COLUMNS]
        max_slip, rear_slip = max(slips), max(slips[2:])
        brake_change = abs(brake - self.previous_brake)
        self.previous_brake = brake
        rpm_ratio = _clamp(row.get("rpm", 0.0) / max(row.get("max_rpm", 1.0), 1.0))
        abs_active = bool(row.get("abs_active", False))
        rough = (not bool(row.get("on_track", True))) or str(row.get("surface_type", "")).lower() in {"rough", "gravel", "dirt", "grass"}
        collision = _clamp(row.get("collision_intensity", 0.0))
        lateral = _clamp(abs(float(row.get("accel_y", 0.0))) / 10.0)
        feedback = {
            "left_trigger_resistance": _clamp((brake - self.config.get("brake_resistance_threshold", .55)) / .45),
            "right_trigger_resistance": _clamp((throttle - .45) * .45),
            "left_trigger_pulse": _clamp(max(1.0 if abs_active else 0.0, brake_change / max(self.config.get("abs_pulse_threshold", .12), .01))),
            "right_trigger_pulse": _clamp((rear_slip - self.config.get("wheel_slip_threshold", .35)) / .65 * throttle),
            "vibration_left": _clamp(max(max_slip, 0.55 if rough else 0.0, collision, lateral * .3)),
            "vibration_right": _clamp(max(max_slip * .85, 0.55 if rough else 0.0, collision, lateral * .3)),
            "vibration_frequency": _clamp((rpm_ratio - self.config.get("rpm_vibration_threshold", .72)) / .28),
        }
        event = "collision" if collision >= self.config.get("collision_vibration_threshold", .15) else "off_track" if rough else "wheel_slip" if max_slip >= self.config.get("wheel_slip_threshold", .35) else "none"
        feedback["haptic_event"] = event
        # Labels have the same low-latency smoothing behavior as runtime output.
        return self.smoother.apply({key: _clamp(value) if key in HAPTIC_COLUMNS else value for key, value in feedback.items()})
