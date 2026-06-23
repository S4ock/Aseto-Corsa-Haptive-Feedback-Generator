import pandas as pd

from src.training.features import build_feature_frame


def test_feature_windows_are_causal_and_complete():
    rows = [{"session_id": "a", "timestamp": index, "speed_kmh": index * 10, "rpm": 1000, "max_rpm": 8000, "throttle": .5, "brake": 0, "steering": .1, "wheel_slip_fl": 0, "wheel_slip_fr": 0, "wheel_slip_rl": .2, "wheel_slip_rr": .3} for index in range(4)]
    features = build_feature_frame(pd.DataFrame(rows), window_size=3)
    assert len(features) == 4
    assert features.loc[2, "rolling_mean_speed"] == 10
    assert "average_wheel_slip" in features and "brake_change_rate" in features
