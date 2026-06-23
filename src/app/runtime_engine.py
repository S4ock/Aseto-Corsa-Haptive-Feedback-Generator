from __future__ import annotations

import time
from collections import deque

import pandas as pd

from src.haptics.smoothing import FeedbackSmoother
from src.training.features import build_feature_frame


class RuntimeEngine:
    def __init__(self, model, preprocessor: dict, smoothing_factor: float = .35):
        self.model = model
        self.preprocessor = preprocessor
        self.history = deque(maxlen=max(2, int(preprocessor.get("window_size", 15))))
        self.smoother = FeedbackSmoother(smoothing_factor)
        self.inference_interval = 1.0 / max(1, int(preprocessor.get("inference_hz", 60)))
        self.next_inference_at = 0.0
        self.last_feedback = {"left_trigger_resistance": 0.0, "right_trigger_resistance": 0.0, "left_trigger_pulse": 0.0, "right_trigger_pulse": 0.0, "vibration_left": 0.0, "vibration_right": 0.0, "vibration_frequency": 0.0, "haptic_event": "none"}

    def predict(self, telemetry: dict) -> tuple[dict, float]:
        now = time.monotonic()
        if now < self.next_inference_at:
            return self.last_feedback, 0.0
        self.next_inference_at = now + self.inference_interval
        self.history.append(telemetry)
        frame = pd.DataFrame(self.history)
        features = build_feature_frame(frame, int(self.preprocessor.get("window_size", 15)))
        columns = self.preprocessor["feature_columns"]
        transformed = self.preprocessor["transformer"].transform(features.reindex(columns=columns, fill_value=0).tail(1))
        start = time.perf_counter()
        values = self.model.predict(transformed)[0]
        latency_ms = (time.perf_counter() - start) * 1000
        names = ["left_trigger_resistance", "right_trigger_resistance", "left_trigger_pulse", "right_trigger_pulse", "vibration_left", "vibration_right", "vibration_frequency"]
        feedback = {name: float(value) for name, value in zip(names, values)}
        feedback["haptic_event"] = "predicted"
        self.last_feedback = self.smoother.apply(feedback)
        return self.last_feedback, latency_ms
