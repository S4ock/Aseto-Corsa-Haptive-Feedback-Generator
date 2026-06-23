"""Conversion of adapter packets to a forgiving, shared telemetry schema."""
from __future__ import annotations

import math
import time
from typing import Any

from src.constants import CONTROL_COLUMNS, SLIP_COLUMNS, TELEMETRY_COLUMNS


def _number(value: Any, default: float = float("nan")) -> float:
    try:
        value = float(value)
        return value if math.isfinite(value) else default
    except (TypeError, ValueError):
        return default


def _first(packet: dict[str, Any], *names: str, default: Any = float("nan")) -> Any:
    for name in names:
        if name in packet and packet[name] is not None:
            return packet[name]
    return default


def normalize(packet: dict[str, Any], game: str, session_id: str) -> dict[str, Any]:
    """Return all canonical fields; absent source fields stay safe and explicit."""
    row: dict[str, Any] = {name: float("nan") for name in TELEMETRY_COLUMNS}
    row.update({
        "timestamp": _number(_first(packet, "timestamp", default=time.time()), time.time()),
        "game": game,
        "session_id": session_id,
        "speed_kmh": _number(_first(packet, "speed_kmh", "speed", "Speed")),
        "rpm": _number(_first(packet, "rpm", "current_engine_rpm", "CurrentEngineRpm")),
        "max_rpm": _number(_first(packet, "max_rpm", "engine_max_rpm", "EngineMaxRpm")),
        "gear": _number(_first(packet, "gear", "Gear")),
        "throttle": _number(_first(packet, "throttle", "accel", "Accel"), 0.0),
        "brake": _number(_first(packet, "brake", "Brake"), 0.0),
        "clutch": _number(_first(packet, "clutch", "Clutch"), 0.0),
        "steering": _number(_first(packet, "steering", "steer", "Steer"), 0.0),
        "accel_x": _number(_first(packet, "accel_x", "AccelerationX"), 0.0),
        "accel_y": _number(_first(packet, "accel_y", "AccelerationY"), 0.0),
        "accel_z": _number(_first(packet, "accel_z", "AccelerationZ"), 0.0),
        "velocity_x": _number(_first(packet, "velocity_x", "VelocityX"), 0.0),
        "velocity_y": _number(_first(packet, "velocity_y", "VelocityY"), 0.0),
        "velocity_z": _number(_first(packet, "velocity_z", "VelocityZ"), 0.0),
        "surface_type": str(_first(packet, "surface_type", "surface", default="unknown")),
        "on_track": bool(_first(packet, "on_track", default=True)),
        "collision_intensity": _number(_first(packet, "collision_intensity"), 0.0),
        "abs_active": bool(_first(packet, "abs_active", default=False)),
        "traction_control_active": bool(_first(packet, "traction_control_active", default=False)),
    })
    for wheel in ("fl", "fr", "rl", "rr"):
        row[f"wheel_slip_{wheel}"] = _number(_first(packet, f"wheel_slip_{wheel}", f"TireSlipRatio{wheel.upper()}"), 0.0)
        row[f"tire_temp_{wheel}"] = _number(_first(packet, f"tire_temp_{wheel}"))
    # Some sources report m/s; only their explicit 'speed_mps' is converted.
    if "speed_mps" in packet:
        row["speed_kmh"] = _number(packet["speed_mps"], 0.0) * 3.6
    for name in CONTROL_COLUMNS:
        row[name] = max(0.0, min(1.0, row[name]))
    row["steering"] = max(-1.0, min(1.0, row["steering"]))
    for name in SLIP_COLUMNS + ["collision_intensity"]:
        row[name] = max(0.0, min(1.0, row[name]))
    return row
