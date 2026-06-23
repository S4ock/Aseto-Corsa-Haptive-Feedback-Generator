from src.constants import TELEMETRY_COLUMNS
from src.telemetry.normalizer import normalize


def test_normalizer_returns_complete_clamped_schema():
    row = normalize({"speed_mps": 10, "throttle": 2, "brake": -2, "steering": 3, "wheel_slip_rl": 4}, "mock", "s1")
    assert set(TELEMETRY_COLUMNS).issubset(row)
    assert row["speed_kmh"] == 36
    assert row["throttle"] == 1 and row["brake"] == 0 and row["steering"] == 1
    assert row["wheel_slip_rl"] == 1
    assert row["game"] == "mock" and row["session_id"] == "s1"
