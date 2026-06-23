from __future__ import annotations

import json
import itertools
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import train_test_split
from sklearn.multioutput import MultiOutputRegressor
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.training.dataset_builder import build_dataset, save_training_table
from src.training.evaluate import evaluate_predictions
from src.training.model_io import save_artifacts

try:
    from catboost import CatBoostRegressor
except ImportError:  # The rest of the research pipeline remains usable without it.
    CatBoostRegressor = None

try:
    import torch
    from torch import nn
    from torch.utils.data import DataLoader, TensorDataset
except ImportError:  # CUDA/PyTorch is an optional accelerated model backend.
    torch = None
    nn = None
    DataLoader = None
    TensorDataset = None


class PerOutputCatBoostRegressor:
    """CatBoost multi-output adapter that safely handles all-zero haptic targets."""

    def __init__(self, seed: int):
        self.seed = seed

    def fit(self, x, y):
        values = np.asarray(y, dtype=float)
        if values.ndim == 1:
            values = values.reshape(-1, 1)
        self.models_ = []
        self.constants_ = []
        for index in range(values.shape[1]):
            target = values[:, index]
            if np.ptp(target) <= 1e-12:
                self.models_.append(None)
                self.constants_.append(float(target[0]))
                continue
            model = CatBoostRegressor(
                loss_function="RMSE", iterations=300, depth=6, learning_rate=.05,
                random_seed=self.seed, verbose=False, thread_count=-1,
            )
            model.fit(x, target)
            self.models_.append(model)
            self.constants_.append(None)
        return self

    def predict(self, x):
        outputs = []
        for model, constant in zip(self.models_, self.constants_):
            outputs.append(np.full(len(x), constant) if model is None else model.predict(x))
        return np.column_stack(outputs)

    @property
    def feature_importances_(self):
        importances = [model.feature_importances_ for model in self.models_ if model is not None]
        return np.mean(importances, axis=0) if importances else np.array([])


class TorchDeepMLPRegressor:
    """Portable PyTorch regressor: trains on CUDA, stores weights on CPU."""

    def __init__(self, seed: int, config: dict[str, Any] | None = None):
        self.seed = seed
        self.config = config or {}
        self.training_device = None

    def fit(self, x, y):
        if torch is None:
            raise RuntimeError("PyTorch is unavailable. Install requirements-cuda.txt before training the CUDA model.")
        requested_device = self.config.get("device", "cuda")
        cuda_available = torch.cuda.is_available()
        if requested_device == "cuda" and not cuda_available and self.config.get("require_cuda", True):
            raise RuntimeError("CUDA was requested but PyTorch cannot see an NVIDIA CUDA device. Install the CUDA PyTorch wheel from requirements-cuda.txt.")
        device = torch.device("cuda" if requested_device == "cuda" and cuda_available else "cpu")
        self.training_device = str(device)
        torch.manual_seed(self.seed)
        if cuda_available:
            torch.cuda.manual_seed_all(self.seed)
        inputs = np.asarray(x, dtype=np.float32)
        targets = np.asarray(y, dtype=np.float32)
        self.input_size, self.output_size = inputs.shape[1], targets.shape[1]
        model = self._build_model().to(device)
        loader = DataLoader(
            TensorDataset(torch.from_numpy(inputs), torch.from_numpy(targets)),
            batch_size=max(32, int(self.config.get("batch_size", 512))), shuffle=True,
            pin_memory=device.type == "cuda",
        )
        optimizer = torch.optim.AdamW(model.parameters(), lr=float(self.config.get("learning_rate", .001)), weight_decay=1e-5)
        loss_fn = nn.SmoothL1Loss()
        model.train()
        for _epoch in range(max(1, int(self.config.get("epochs", 35)))):
            for batch_x, batch_y in loader:
                batch_x, batch_y = batch_x.to(device, non_blocking=True), batch_y.to(device, non_blocking=True)
                optimizer.zero_grad(set_to_none=True)
                loss_fn(model(batch_x), batch_y).backward()
                optimizer.step()
        # CPU state dict keeps joblib artefacts portable and avoids serializing GPU handles.
        self.state_dict_ = {name: value.detach().cpu() for name, value in model.state_dict().items()}
        self._inference_model = None
        self._inference_device = None
        return self

    def predict(self, x):
        if torch is None or not hasattr(self, "state_dict_"):
            raise RuntimeError("CUDA model has not been fitted or PyTorch is unavailable.")
        device = torch.device("cuda" if torch.cuda.is_available() and self.config.get("device", "cuda") == "cuda" else "cpu")
        if getattr(self, "_inference_model", None) is None or self._inference_device != str(device):
            model = self._build_model()
            model.load_state_dict(self.state_dict_)
            self._inference_model = model.to(device).eval()
            self._inference_device = str(device)
        model = self._inference_model
        values = np.asarray(x, dtype=np.float32)
        batches = []
        with torch.no_grad():
            for start in range(0, len(values), 4096):
                batch = torch.from_numpy(values[start:start + 4096]).to(device)
                batches.append(model(batch).cpu().numpy())
        return np.vstack(batches)

    def __getstate__(self):
        state = self.__dict__.copy()
        # Rebuild inference modules after loading; persist only CPU tensors.
        state["_inference_model"] = None
        state["_inference_device"] = None
        return state

    def _build_model(self):
        layers: list[Any] = []
        input_size = self.input_size
        for width in self.config.get("hidden_layers", [192, 128, 64]):
            layers.extend([nn.Linear(input_size, int(width)), nn.ReLU(), nn.LayerNorm(int(width)), nn.Dropout(.08)])
            input_size = int(width)
        layers.extend([nn.Linear(input_size, self.output_size), nn.Sigmoid()])
        return nn.Sequential(*layers)


def _models(seed: int, requested: list[str] | None = None, deep_learning: dict[str, Any] | None = None) -> dict:
    models = {
        "random_forest": RandomForestRegressor(n_estimators=80, min_samples_leaf=2, random_state=seed, n_jobs=-1),
        "hist_gradient_boosting": MultiOutputRegressor(HistGradientBoostingRegressor(max_iter=100, random_state=seed)),
        "mlp": MLPRegressor(hidden_layer_sizes=(48, 24), max_iter=300, early_stopping=True, random_state=seed),
    }
    if CatBoostRegressor is not None:
        models["catboost"] = PerOutputCatBoostRegressor(seed)
    if torch is not None:
        models["torch_deep_mlp"] = TorchDeepMLPRegressor(seed, deep_learning)
    requested = requested or list(models)
    unavailable = [name for name in requested if name not in models]
    if unavailable:
        raise RuntimeError(f"Requested models are unavailable: {', '.join(unavailable)}. Run 'python -m pip install -r requirements.txt'.")
    return {name: models[name] for name in requested}


def _session_validation_mask(groups: pd.Series, validation_fraction: float = .2) -> np.ndarray:
    """Choose whole validation sessions without accidentally training on a tiny session."""
    counts = groups.value_counts(sort=False)
    sessions = list(counts.index)
    if len(sessions) == 1:
        mask = np.zeros(len(groups), dtype=bool)
        mask[max(1, int(len(groups) * (1 - validation_fraction))):] = True
        return mask
    total = len(groups)
    target = total * validation_fraction
    candidates = []
    # Session counts are usually small. Limit combinatorics for unusually large studies.
    max_holdout = min(len(sessions) - 1, 3)
    for size in range(1, max_holdout + 1):
        for held_out in itertools.combinations(sessions, size):
            validation_rows = int(counts.loc[list(held_out)].sum())
            training_rows = total - validation_rows
            if training_rows >= max(8, total * .5):
                candidates.append((abs(validation_rows - target), held_out))
    if not candidates:
        # Fall back to holding out the smallest session, preserving the largest training set.
        held_out = (counts.sort_values().index[0],)
    else:
        held_out = min(candidates, key=lambda item: item[0])[1]
    return groups.isin(held_out).to_numpy()


def train(frame: pd.DataFrame, config: dict, results_dir: str | Path = "results") -> dict:
    features, targets, metadata = build_dataset(frame, int(config.get("window_size", 15)), int(config.get("resample_hz", 60)))
    save_training_table(features, targets, metadata)
    train_games = set(config.get("train_games", ["f1_25", "forza_horizon_5", "mock"]))
    train_mask = pd.Series(True, index=metadata.index) if config.get("include_all_games", False) else metadata["game"].isin(train_games)
    if train_mask.sum() < 8:
        raise ValueError("Need at least eight rows from configured training games.")
    x, y, groups = features.loc[train_mask], targets.loc[train_mask], metadata.loc[train_mask, "session_id"]
    validation_strategy = config.get("validation_strategy", "group_by_session")
    if validation_strategy in {"random_row_split", "random_row_85_15"}:
        fit_indices, validation_indices = train_test_split(
            np.arange(len(x)), test_size=float(config.get("validation_fraction", .15)),
            random_state=int(config.get("random_seed", 25)), shuffle=True,
        )
        fit_mask = np.zeros(len(x), dtype=bool); fit_mask[fit_indices] = True
        valid_mask = np.zeros(len(x), dtype=bool); valid_mask[validation_indices] = True
    elif validation_strategy == "group_by_session":
        valid_mask = _session_validation_mask(groups)
        fit_mask = ~valid_mask
    else:
        raise ValueError(f"Unsupported validation_strategy: {validation_strategy}")
    if fit_mask.sum() < 2 or valid_mask.sum() < 1:
        raise ValueError("Record more telemetry rows to build a validation split.")
    preprocessor = Pipeline([("imputer", SimpleImputer(strategy="median")), ("scaler", StandardScaler())])
    x_fit = preprocessor.fit_transform(x.loc[fit_mask])
    x_valid = preprocessor.transform(x.loc[valid_mask])
    scores, fitted = {}, {}
    requested_models = list(config.get("models", ["random_forest", "hist_gradient_boosting", "mlp"]))
    deep_learning = config.get("deep_learning", {})
    for name, model in _models(int(config.get("random_seed", 25)), requested_models, deep_learning).items():
        model.fit(x_fit, y.loc[fit_mask])
        scores[name] = float(mean_absolute_error(y.loc[valid_mask], model.predict(x_valid)))
        fitted[name] = model
    best_name = min(scores, key=scores.get)
    best_model = fitted[best_name]
    metrics = evaluate_predictions(y.loc[valid_mask], best_model.predict(x_valid), best_model, x_valid, results_dir)
    metrics.update({"best_model": best_name, "validation_mae_by_model": scores, "training_rows": int(fit_mask.sum()), "validation_rows": int(valid_mask.sum())})
    # Refit the selected model on all eligible training data for runtime use.
    final_preprocessor = Pipeline([("imputer", SimpleImputer(strategy="median")), ("scaler", StandardScaler())])
    x_all = final_preprocessor.fit_transform(x)
    final_model = _models(int(config.get("random_seed", 25)), requested_models, deep_learning)[best_name].fit(x_all, y)
    test_game = config.get("test_game")
    test_mask = metadata["game"] == test_game if test_game else pd.Series(False, index=metadata.index)
    if test_game and test_mask.any() and not config.get("include_all_games", False):
        x_test = final_preprocessor.transform(features.loc[test_mask])
        cross_game_metrics = evaluate_predictions(targets.loc[test_mask], final_model.predict(x_test), final_model, x_test, results_dir)
        metrics["cross_game_test"] = {"game": test_game, "rows": int(test_mask.sum()), **cross_game_metrics}
    elif test_game:
        metrics["cross_game_test"] = {"game": test_game, "status": "No held-out recordings available."}
    metrics["validation_strategy"] = validation_strategy
    if hasattr(final_model, "training_device"):
        metrics["training_device"] = final_model.training_device
    save_artifacts(final_model, {"transformer": final_preprocessor, "feature_columns": list(features.columns), "window_size": int(config.get("window_size", 15)), "inference_hz": int(config.get("resample_hz", 60))})
    if hasattr(final_model, "feature_importances_"):
        pd.DataFrame({"feature": features.columns, "importance": final_model.feature_importances_}).sort_values("importance", ascending=False).to_csv(Path(results_dir) / "feature_importance.csv", index=False)
    Path(results_dir).mkdir(parents=True, exist_ok=True)
    (Path(results_dir) / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics
