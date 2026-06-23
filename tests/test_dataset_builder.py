import pandas as pd

from src.constants import HAPTIC_COLUMNS
from src.training.dataset_builder import build_dataset, resample_sessions


def test_dataset_builder_keeps_targets_and_metadata():
    row = {"session_id": "s", "game": "mock", "timestamp": 1, "speed_kmh": 5, "rpm": 1000, "max_rpm": 8000}
    row.update({column: 0.2 for column in HAPTIC_COLUMNS})
    features, targets, metadata = build_dataset(pd.DataFrame([row]), 3)
    assert len(features) == len(targets) == len(metadata) == 1
    assert list(targets.columns) == HAPTIC_COLUMNS
    assert metadata.loc[0, "game"] == "mock"


def test_resampler_uses_fixed_time_bins_and_preserves_collision_peak():
    frame = pd.DataFrame([
        {"game": "mock", "session_id": "s", "timestamp": 0.001, "speed_kmh": 10, "collision_intensity": 0, "haptic_event": "none"},
        {"game": "mock", "session_id": "s", "timestamp": 0.010, "speed_kmh": 20, "collision_intensity": 1, "haptic_event": "collision"},
    ])
    result = resample_sessions(frame, 60)
    assert len(result) == 1
    assert result.loc[0, "collision_intensity"] == 1
    assert result.loc[0, "haptic_event"] == "collision"
