from __future__ import annotations

from src.constants import HAPTIC_COLUMNS


class FeedbackSmoother:
    def __init__(self, alpha: float = 0.35):
        self.alpha = max(0.0, min(1.0, float(alpha)))
        self.previous = {column: 0.0 for column in HAPTIC_COLUMNS}

    def apply(self, feedback: dict) -> dict:
        result = dict(feedback)
        for column in HAPTIC_COLUMNS:
            current = max(0.0, min(1.0, float(feedback.get(column, 0.0))))
            value = self.alpha * current + (1.0 - self.alpha) * self.previous[column]
            self.previous[column] = value
            result[column] = value
        return result
