"""Standalone, output-only USB DualSense motor and trigger check.

No game, telemetry source, controller inputs, or virtual devices are involved.
"""
from __future__ import annotations

import argparse
import time

from src.haptics.dualsense_output import create_output
from src.utils.config_loader import load_yaml
from src.utils.safety import enforce_safe_mode, print_startup_warning


def main() -> None:
    parser = argparse.ArgumentParser(description="Test USB DualSense motors and adaptive triggers only.")
    parser.add_argument("--seconds", type=float, default=1.0, help="Length of each test pulse.")
    args = parser.parse_args()
    duration = max(.1, min(5.0, args.seconds))
    games = load_yaml("games.yaml")
    enforce_safe_mode(games, "mock", "dualsense")
    print_startup_warning()
    output = create_output("dualsense", games.get("dualsense", {}))
    patterns = [
        ("left motor", {"vibration_left": .8, "vibration_right": 0.0}),
        ("right motor", {"vibration_left": 0.0, "vibration_right": .8}),
        ("both motors", {"vibration_left": .7, "vibration_right": .7}),
        ("left brake trigger", {"left_trigger_resistance": .7}),
        ("right traction trigger", {"right_trigger_resistance": .7}),
    ]
    try:
        output.connect()
        for label, feedback in patterns:
            print(f"Testing {label} for {duration:.1f} seconds...")
            output.send_feedback(feedback)
            time.sleep(duration)
            output.stop()
            time.sleep(.3)
    finally:
        output.stop()
        output.close()
    print("DualSense motor and adaptive-trigger test finished.")


if __name__ == "__main__":
    main()
