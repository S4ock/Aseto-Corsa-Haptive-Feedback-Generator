from pathlib import Path

import joblib


def save_artifacts(model, preprocessor: dict, model_path: str | Path = "models/best_model.pkl", preprocessor_path: str | Path = "models/preprocessor.pkl") -> None:
    Path(model_path).parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, model_path)
    joblib.dump(preprocessor, preprocessor_path)


def load_artifacts(model_path: str | Path, preprocessor_path: str | Path = "models/preprocessor.pkl"):
    return joblib.load(model_path), joblib.load(preprocessor_path)
