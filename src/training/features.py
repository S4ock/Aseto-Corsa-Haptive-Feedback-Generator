from __future__ import annotations

import numpy as np
import pandas as pd

from src.constants import SLIP_COLUMNS

BASE_FEATURES = [
    "speed_kmh", "rpm", "max_rpm", "gear", "throttle", "brake", "steering",
    "accel_x", "accel_y", "accel_z", "velocity_x", "velocity_y", "velocity_z",
    *SLIP_COLUMNS, "collision_intensity", "abs_active", "traction_control_active", "on_track",
]


def build_feature_frame(frame: pd.DataFrame, window_size: int = 15) -> pd.DataFrame:
    """Create causal, per-session features that runtime can reproduce row by row."""
    data = frame.copy().sort_values(["session_id", "timestamp"], kind="stable")
    for name in BASE_FEATURES:
        values = data[name] if name in data else pd.Series(0.0, index=data.index)
        if name in {"abs_active", "traction_control_active", "on_track"}:
            values = values.astype(str).str.lower().map({"true": 1.0, "false": 0.0, "1": 1.0, "0": 0.0})
        data[name] = pd.to_numeric(values, errors="coerce").fillna(0.0)
    data["rpm_ratio"] = (data["rpm"] / data["max_rpm"].replace(0, np.nan)).fillna(0.0).clip(0, 1)
    data["average_wheel_slip"] = data[SLIP_COLUMNS].mean(axis=1)
    data["max_wheel_slip"] = data[SLIP_COLUMNS].max(axis=1)
    groups = data.groupby("session_id", sort=False)
    for source, target in [("brake", "brake_change_rate"), ("throttle", "throttle_change_rate"), ("steering", "steering_change_rate"), ("rpm", "rpm_change_rate")]:
        data[target] = groups[source].diff().fillna(0.0)
    data["rolling_mean_speed"] = groups["speed_kmh"].transform(lambda x: x.rolling(window_size, min_periods=1).mean())
    data["rolling_std_steering"] = groups["steering"].transform(lambda x: x.rolling(window_size, min_periods=1).std()).fillna(0.0)
    data["rolling_max_tire_slip"] = groups["max_wheel_slip"].transform(lambda x: x.rolling(window_size, min_periods=1).max())
    feature_columns = BASE_FEATURES + [
        "rpm_ratio", "average_wheel_slip", "max_wheel_slip", "brake_change_rate",
        "throttle_change_rate", "steering_change_rate", "rpm_change_rate", "rolling_mean_speed",
        "rolling_std_steering", "rolling_max_tire_slip",
    ]
    return data[feature_columns].replace([np.inf, -np.inf], np.nan).fillna(0.0)
