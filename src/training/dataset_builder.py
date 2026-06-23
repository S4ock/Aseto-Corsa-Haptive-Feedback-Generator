from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.constants import HAPTIC_COLUMNS, HAPTIC_EVENT_COLUMN, TELEMETRY_COLUMNS
from src.training.features import build_feature_frame


def load_processed_sessions(directory: str | Path = "data/processed") -> pd.DataFrame:
    paths = [path for path in Path(directory).glob("*_processed.csv") if path.name != "training_table.csv"]
    if not paths:
        raise FileNotFoundError("No processed recordings found. Run the mock recorder first.")
    return pd.concat([pd.read_csv(path) for path in paths], ignore_index=True)


def build_dataset(frame: pd.DataFrame, window_size: int = 15, resample_hz: int = 60) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    frame = resample_sessions(frame, resample_hz)
    features = build_feature_frame(frame, window_size)
    targets = frame.reindex(columns=HAPTIC_COLUMNS).apply(pd.to_numeric, errors="coerce").fillna(0.0).clip(0, 1)
    metadata = frame.reindex(columns=["session_id", "game"]).fillna("unknown")
    return features, targets, metadata


def resample_sessions(frame: pd.DataFrame, sample_rate_hz: int = 60) -> pd.DataFrame:
    """Bin all sessions to one causal time base so games with different packet rates align."""
    if frame.empty or sample_rate_hz <= 0:
        return frame.copy()
    metadata_columns = {"game", "session_id", "surface_type"}
    numeric = [name for name in set(TELEMETRY_COLUMNS + HAPTIC_COLUMNS + ["collision_intensity"]) if name in frame and name not in metadata_columns]
    boolean_columns = [name for name in ("abs_active", "traction_control_active", "on_track") if name in frame]
    outputs = []
    for _, session in frame.groupby(["game", "session_id"], dropna=False, sort=False):
        data = session.copy()
        data["timestamp"] = pd.to_numeric(data["timestamp"], errors="coerce")
        data = data.dropna(subset=["timestamp"]).sort_values("timestamp", kind="stable")
        if data.empty:
            continue
        for column in numeric:
            if column in boolean_columns:
                data[column] = data[column].astype(str).str.lower().map({"true": 1.0, "false": 0.0, "1": 1.0, "0": 0.0})
            else:
                data[column] = pd.to_numeric(data[column], errors="coerce")
        origin = float(data["timestamp"].iloc[0])
        data["_bin"] = ((data["timestamp"] - origin) * sample_rate_hz).clip(lower=0).astype(int)
        grouped = data.groupby("_bin", sort=True)
        reduced = grouped.last()
        continuous = [name for name in numeric if name not in HAPTIC_COLUMNS + ["collision_intensity"] + boolean_columns]
        if continuous:
            means = grouped[continuous].mean()
            for column in continuous:
                # Assignment by column replaces the source dtype (rather than coercing into it).
                reduced[column] = means[column]
        peaks = [name for name in HAPTIC_COLUMNS + ["collision_intensity"] if name in data]
        if peaks:
            reduced.loc[:, peaks] = grouped[peaks].max()
        for column in ("abs_active", "traction_control_active"):
            if column in data:
                reduced[column] = grouped[column].max()
        if "on_track" in data:
            reduced["on_track"] = grouped["on_track"].min()
        if HAPTIC_EVENT_COLUMN in data:
            reduced[HAPTIC_EVENT_COLUMN] = grouped[HAPTIC_EVENT_COLUMN].agg(_priority_event)
        outputs.append(reduced.drop(columns=["_bin"], errors="ignore").reset_index(drop=True))
    return pd.concat(outputs, ignore_index=True) if outputs else frame.iloc[0:0].copy()


def _priority_event(events: pd.Series) -> str:
    values = {str(value) for value in events}
    for event in ("collision", "off_track", "wheel_slip"):
        if event in values:
            return event
    return "none"


def save_training_table(features: pd.DataFrame, targets: pd.DataFrame, metadata: pd.DataFrame, path: str | Path = "data/processed/training_table.csv") -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    pd.concat([metadata.reset_index(drop=True), features.reset_index(drop=True), targets.reset_index(drop=True)], axis=1).to_csv(output, index=False)
    return output
