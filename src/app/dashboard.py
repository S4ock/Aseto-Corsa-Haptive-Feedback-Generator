from src.constants import HAPTIC_COLUMNS


def render_status(game: str, packet_rate: float, telemetry: dict, feedback: dict, latency_ms: float) -> str:
    values = [
        f"game={game}", f"safe_mode=true", f"packets/s={packet_rate:.1f}",
        f"speed={telemetry.get('speed_kmh', 0):.1f}km/h", f"rpm={telemetry.get('rpm', 0):.0f}",
        f"gear={telemetry.get('gear', 0):.0f}", f"throttle={telemetry.get('throttle', 0):.2f}",
        f"brake={telemetry.get('brake', 0):.2f}", f"steering={telemetry.get('steering', 0):.2f}",
        f"slip={max(telemetry.get('wheel_slip_fl', 0), telemetry.get('wheel_slip_fr', 0), telemetry.get('wheel_slip_rl', 0), telemetry.get('wheel_slip_rr', 0)):.2f}",
        f"collision={telemetry.get('collision_intensity', 0):.2f}",
        *(f"{name}={feedback.get(name, 0):.2f}" for name in HAPTIC_COLUMNS),
        f"inference={latency_ms:.2f}ms",
    ]
    return " | ".join(values)
