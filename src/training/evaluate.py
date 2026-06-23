from __future__ import annotations

import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from src.constants import HAPTIC_COLUMNS


def evaluate_predictions(y_true, y_pred, model, x_transformed, output_dir: str | Path = "results") -> dict:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    y_true, y_pred = np.asarray(y_true), np.clip(np.asarray(y_pred), 0, 1)
    per_output = {name: float(mean_absolute_error(y_true[:, index], y_pred[:, index])) for index, name in enumerate(HAPTIC_COLUMNS)}
    start = time.perf_counter()
    model.predict(x_transformed[:1])
    latency_ms = (time.perf_counter() - start) * 1000
    smoothness = float(np.mean(np.abs(np.diff(y_pred, axis=0)))) if len(y_pred) > 1 else 0.0
    metrics = {
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": float(mean_squared_error(y_true, y_pred) ** .5),
        "r2": float(r2_score(y_true, y_pred, multioutput="uniform_average")),
        "per_output_mae": per_output,
        "inference_latency_ms": latency_ms,
        "smoothness_score": smoothness,
    }
    plt.figure(figsize=(6, 4)); plt.scatter(y_true.ravel(), y_pred.ravel(), s=4, alpha=.4); plt.xlabel("Rule target"); plt.ylabel("Prediction"); plt.tight_layout(); plt.savefig(output / "predicted_vs_true.png"); plt.close()
    plt.figure(figsize=(6, 4)); plt.hist((y_pred - y_true).ravel(), bins=30); plt.xlabel("Prediction error"); plt.tight_layout(); plt.savefig(output / "error_distribution.png"); plt.close()
    plt.figure(figsize=(8, 4)); plt.bar(per_output.keys(), per_output.values()); plt.xticks(rotation=40, ha="right"); plt.ylabel("MAE"); plt.tight_layout(); plt.savefig(output / "per_output_mae.png"); plt.close()
    return metrics
