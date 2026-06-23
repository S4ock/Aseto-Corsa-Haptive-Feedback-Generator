from pathlib import Path

import joblib


def save_artifacts(model, preprocessor: dict, model_path: str | Path = "models/best_model.pkl", preprocessor_path: str | Path = "models/preprocessor.pkl") -> None:
    Path(model_path).parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, model_path)
    joblib.dump(preprocessor, preprocessor_path)


def load_artifacts(model_path: str | Path, preprocessor_path: str | Path | None = None):
    """Load a model with the matching preprocessor stored beside it.

    This keeps a copied model folder and the packaged desktop application
    self-contained. Callers may still provide an explicit path for older
    layouts.
    """
    model_path = Path(model_path)
    preprocessor_path = Path(preprocessor_path) if preprocessor_path is not None else model_path.with_name("preprocessor.pkl")
    return joblib.load(model_path), joblib.load(preprocessor_path)
