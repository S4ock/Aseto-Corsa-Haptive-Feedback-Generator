from __future__ import annotations

import json
from pathlib import Path

from src.constants import HAPTIC_COLUMNS
from src.training.features import BASE_FEATURES


SAFETY_STATEMENT = "This project only reads official telemetry and outputs haptic/adaptive-trigger feedback. It does not modify gameplay, does not automate inputs, does not read/write game memory, and was designed for offline research."


def generate_report() -> Path:
    processed = list(Path("data/processed").glob("*_processed.csv"))
    metadata = []
    for path in Path("data/raw").glob("*_metadata.json"):
        metadata.append(json.loads(path.read_text(encoding="utf-8")))
    metrics_path = Path("results/metrics.json")
    metrics = json.loads(metrics_path.read_text(encoding="utf-8")) if metrics_path.exists() else {"status": "Training has not been run."}
    rows = sum(max(0, len(path.read_text(encoding="utf-8").splitlines()) - 1) for path in processed)
    games = sorted({item.get("game", "unknown") for item in metadata})
    event_counts = {}
    for path in processed:
        lines = path.read_text(encoding="utf-8").splitlines()
        if lines:
            headers = lines[0].split(",")
            if "haptic_event" in headers:
                event_index = headers.index("haptic_event")
                for line in lines[1:]:
                    values = line.split(",")
                    if len(values) > event_index:
                        event_counts[values[event_index]] = event_counts.get(values[event_index], 0) + 1
    report = f"""# TelemetryDualSenseAI research evidence report

## Project goal

Offline research into predicting custom DualSense-style haptic feedback from officially exposed racing telemetry for accessibility and immersion.

## Dataset evidence

- Sessions: {len(metadata)}
- Processed rows: {rows}
- Games recorded: {', '.join(games) or 'none'}
- Training games: F1 25 and Forza Horizon 5
- Test game: Assetto Corsa

## Method

- Features: {', '.join(BASE_FEATURES)} plus causal rolling/change features.
- Haptic targets: {', '.join(HAPTIC_COLUMNS)}.
- Models: RandomForestRegressor, HistGradientBoostingRegressor, and MLPRegressor.
- Metrics: {json.dumps(metrics, indent=2)}
- Event balance: {json.dumps(event_counts, indent=2)}

## Limitations

Rule-generated labels are research proxies, not commercial-game haptic captures. Cross-game performance is unavailable until Assetto Corsa recordings are added. Live telemetry adapters only support explicitly configured, documented formats. Collect additional offline examples of off-track, wheel-slip, and collision events when their event counts are much smaller than normal driving.

## Safety statement

{SAFETY_STATEMENT}

## Reproducibility

Install `requirements.txt`, record sessions with `python -m src.main_recorder`, train with `python -m src.main_train`, and run the model with `python -m src.main_runtime --game mock --output stub`.
"""
    output = Path("results/research_evidence_report.md")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")
    return output


if __name__ == "__main__":
    print(f"Wrote {generate_report()}")
