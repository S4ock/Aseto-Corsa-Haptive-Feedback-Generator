from __future__ import annotations

import argparse
import time
from typing import Callable

from src.app.dashboard import render_status
from src.app.runtime_engine import RuntimeEngine
from src.haptics.dualsense_output import create_output
from src.haptics.mixer import RuntimeHapticMixer
from src.telemetry import create_adapter
from src.training.model_io import load_artifacts
from src.utils.config_loader import load_yaml
from src.utils.safety import enforce_safe_mode, print_startup_warning


def run_runtime(game: str, model_path: str, output_mode: str = "stub", max_packets: int | None = None, stop_event=None, status_callback: Callable[[str], None] | None = None) -> None:
    def status(message: str) -> None:
        print(message)
        if status_callback is not None:
            status_callback(message)

    games, haptics = load_yaml("games.yaml"), load_yaml("haptics.yaml")
    enforce_safe_mode(games, game, output_mode)
    print_startup_warning()
    model, preprocessor = load_artifacts(model_path)
    adapter, output = create_adapter(game, games, "runtime"), create_output(output_mode, games.get("dualsense", {}))
    engine = RuntimeEngine(model, preprocessor, haptics.get("smoothing_factor", .35))
    mixer = RuntimeHapticMixer(haptics)
    status("Tip: disable in-game controller rumble to evaluate only the custom haptics output.")
    started, count = time.monotonic(), 0
    try:
        adapter.connect(); output.connect()
        while (stop_event is None or not stop_event.is_set()) and (max_packets is None or count < max_packets):
            packet = adapter.read_packet()
            if packet is None:
                continue
            telemetry = adapter.normalize_packet(packet)
            feedback, latency = engine.predict(telemetry)
            feedback = mixer.apply(telemetry, feedback)
            output.send_feedback(feedback); count += 1
            status(render_status(game, count / max(time.monotonic() - started, .001), telemetry, feedback, latency))
    except KeyboardInterrupt:
        status("Stopping runtime safely...")
    finally:
        output.stop(); output.close(); adapter.close()
        status("Runtime stopped.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Predict output-only haptic feedback from read-only telemetry.")
    parser.add_argument("--game", required=True, choices=["f1_25", "forza_horizon_5", "assetto_corsa", "beamng_drive", "live_for_speed", "mock"])
    parser.add_argument("--model", default="models/best_model.pkl")
    parser.add_argument("--output", choices=["stub", "dualsense"], default="stub")
    parser.add_argument("--max-packets", type=int, default=None, help="Optional packet cap; omit to run until Ctrl+C.")
    args = parser.parse_args()
    run_runtime(args.game, args.model, args.output, args.max_packets)


if __name__ == "__main__":
    main()
