from src.constants import HAPTIC_COLUMNS
from .output_base import HapticOutput


class StubOutput(HapticOutput):
    """Logging only; it cannot create or control a gamepad."""
    def connect(self) -> None:
        print("Stub output connected: haptic predictions will be logged only.")

    def send_feedback(self, feedback_dict: dict) -> None:
        compact = ", ".join(f"{key}={float(feedback_dict.get(key, 0.0)):.2f}" for key in HAPTIC_COLUMNS)
        print(f"HAPTIC_STUB {compact} event={feedback_dict.get('haptic_event', 'none')}")

    def stop(self) -> None:
        return None

    def close(self) -> None:
        return None
