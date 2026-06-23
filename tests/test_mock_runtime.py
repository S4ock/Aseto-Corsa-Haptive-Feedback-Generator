import numpy as np
import pandas as pd

from src.app.runtime_engine import RuntimeEngine
from src.telemetry.mock_telemetry import MockTelemetryAdapter
from src.training.features import build_feature_frame


class DummyModel:
    def predict(self, value):
        return np.full((len(value), 7), .5)


class IdentityTransformer:
    def transform(self, value):
        return value


def test_mock_runtime_prediction_is_bounded():
    adapter = MockTelemetryAdapter({}, "runtime")
    adapter.connect()
    row = adapter.normalize_packet(adapter.read_packet())
    columns = list(build_feature_frame(pd.DataFrame([row])).columns)
    engine = RuntimeEngine(DummyModel(), {"transformer": IdentityTransformer(), "feature_columns": columns, "window_size": 3})
    feedback, latency = engine.predict(row)
    assert all(0 <= value <= 1 for key, value in feedback.items() if key != "haptic_event")
    assert latency >= 0
