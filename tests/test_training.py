import pandas as pd

from src.constants import HAPTIC_COLUMNS
from src.training.train_models import _session_validation_mask, train


def test_session_split_keeps_large_session_for_training():
    groups = pd.Series(["short"] * 200 + ["long"] * 23000)
    validation = _session_validation_mask(groups)
    assert validation.sum() == 200
    assert groups[~validation].nunique() == 1


def test_combined_random_split_is_approximately_80_20(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    rows = []
    for index in range(100):
        row = {"session_id": f"s{index % 2}", "game": "f1_25" if index < 50 else "assetto_corsa", "timestamp": index, "speed_kmh": index, "rpm": 5000, "max_rpm": 9000}
        row.update({column: .2 for column in HAPTIC_COLUMNS})
        rows.append(row)
    metrics = train(pd.DataFrame(rows), {"window_size": 4, "include_all_games": True, "models": ["random_forest"], "validation_strategy": "random_row_split", "validation_fraction": .20, "random_seed": 25}, results_dir="results")
    assert metrics["training_rows"] == 80
    assert metrics["validation_rows"] == 20


def test_model_training_on_small_fake_data(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    rows = []
    for index in range(50):
        row = {"session_id": "fake", "game": "mock", "timestamp": index, "speed_kmh": index, "rpm": 1000 + index * 10, "max_rpm": 8000, "throttle": .4, "brake": .1, "steering": .1, "wheel_slip_fl": .1, "wheel_slip_fr": .1, "wheel_slip_rl": .2, "wheel_slip_rr": .2}
        row.update({column: .2 for column in HAPTIC_COLUMNS})
        rows.append(row)
    metrics = train(pd.DataFrame(rows), {"window_size": 4, "train_games": ["mock"], "random_seed": 1}, results_dir="results")
    assert metrics["best_model"] in {"random_forest", "hist_gradient_boosting", "mlp"}
    assert (tmp_path / "models/best_model.pkl").exists()
