"""Shared schema constants. Keep game-specific names out of the pipeline."""

TELEMETRY_COLUMNS = [
    "timestamp", "game", "session_id", "speed_kmh", "rpm", "max_rpm", "gear",
    "throttle", "brake", "clutch", "steering", "accel_x", "accel_y", "accel_z",
    "velocity_x", "velocity_y", "velocity_z", "wheel_slip_fl", "wheel_slip_fr",
    "wheel_slip_rl", "wheel_slip_rr", "tire_temp_fl", "tire_temp_fr", "tire_temp_rl",
    "tire_temp_rr", "surface_type", "on_track", "collision_intensity", "abs_active",
    "traction_control_active",
]

HAPTIC_COLUMNS = [
    "left_trigger_resistance", "right_trigger_resistance", "left_trigger_pulse",
    "right_trigger_pulse", "vibration_left", "vibration_right", "vibration_frequency",
]

HAPTIC_EVENT_COLUMN = "haptic_event"
SLIP_COLUMNS = ["wheel_slip_fl", "wheel_slip_fr", "wheel_slip_rl", "wheel_slip_rr"]
CONTROL_COLUMNS = ["throttle", "brake", "clutch"]
