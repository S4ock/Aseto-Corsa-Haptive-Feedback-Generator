from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import pandas as pd

from src.haptics.haptic_rules import HapticRuleEngine
from src.telemetry import create_adapter
from src.utils.config_loader import ROOT, load_yaml
from src.utils.safety import enforce_safe_mode, print_startup_warning
from src.utils.time_utils import utc_now_iso


def record_session(game: str, session_name: str, max_packets: int | None = None, stop_event=None, on_telemetry=None) -> tuple[Path, Path]:
    games_config, haptics_config = load_yaml("games.yaml"), load_yaml("haptics.yaml")
    enforce_safe_mode(games_config, game)
    print_startup_warning()
    adapter = create_adapter(game, games_config, session_name)
    rules = HapticRuleEngine(haptics_config)
    raw_path = ROOT / "data" / "raw" / f"{session_name}_raw.jsonl"
    processed_path = ROOT / "data" / "processed" / f"{session_name}_processed.csv"
    metadata_path = ROOT / "data" / "raw" / f"{session_name}_metadata.json"
    count, rows, start = 0, [], time.monotonic()
    interrupted = False
    limit = max_packets or int(games_config.get("recorder", {}).get("max_packets", 500))
    timeout = float(games_config.get("recorder", {}).get("timeout_seconds", 30))
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    processed_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        adapter.connect()
        with raw_path.open("w", encoding="utf-8") as raw_file:
            while (stop_event is None or not stop_event.is_set()) and count < limit and time.monotonic() - start < timeout:
                packet = adapter.read_packet()
                if packet is None:
                    continue
                raw_file.write(json.dumps(packet, default=str) + "\n")
                row = adapter.normalize_packet(packet)
                row.update(rules.label(row))
                if on_telemetry is not None:
                    try:
                        on_telemetry(row)
                    except Exception as error:
                        # Haptic output must never prevent a recording from being saved.
                        print(f"Live haptics callback failed ({error}); continuing recording.")
                rows.append(row); count += 1
                elapsed = max(time.monotonic() - start, .001)
                print(f"packet={count} rate={count/elapsed:.1f}/s speed={row['speed_kmh']:.1f} rpm={row['rpm']:.0f} throttle={row['throttle']:.2f} brake={row['brake']:.2f} steering={row['steering']:.2f} haptic={row['haptic_event']}")
    except KeyboardInterrupt:
        # The handler deliberately surrounds connect/read/flush boundaries too.
        interrupted = True
        print("Stopping recorder safely; saving captured packets...")
    finally:
        adapter.close()
    interrupted = interrupted or (stop_event is not None and stop_event.is_set())
    if not rows:
        raise RuntimeError("No telemetry packets received. Check official telemetry settings or use --game mock.")
    processed_frame = pd.DataFrame(rows)
    processed_frame.to_csv(processed_path, index=False)
    parquet_path = processed_path.with_suffix(".parquet")
    parquet_written = False
    try:
        # Optional: pyarrow/fastparquet is intentionally not a required dependency.
        processed_frame.to_parquet(parquet_path, index=False)
        parquet_written = True
    except (ImportError, ValueError):
        pass
    metadata_path.write_text(json.dumps({"game": game, "session_name": session_name, "start_time": utc_now_iso(), "packets": count, "stopped_by_user": interrupted, "formats": ["csv"] + (["parquet"] if parquet_written else []), "config": games_config}, indent=2), encoding="utf-8")
    ending = "after Ctrl+C" if interrupted else ""
    print(f"Saved {count} packets {ending} to {processed_path}")
    return raw_path, processed_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Record official telemetry and rule-generated haptic labels.")
    parser.add_argument("--game", required=True, choices=["f1_25", "forza_horizon_5", "assetto_corsa", "mock"])
    parser.add_argument("--session-name", required=True)
    parser.add_argument("--max-packets", type=int, default=None)
    args = parser.parse_args()
    record_session(args.game, args.session_name, args.max_packets)


if __name__ == "__main__":
    main()
