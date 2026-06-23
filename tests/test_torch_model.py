import numpy as np
import pytest

from src.training.train_models import TorchDeepMLPRegressor, torch


@pytest.mark.skipif(torch is None, reason="PyTorch is optional")
def test_torch_model_predicts_normalized_multioutput_values():
    x = np.random.default_rng(1).random((24, 4), dtype=np.float32)
    y = np.random.default_rng(2).random((24, 3), dtype=np.float32)
    model = TorchDeepMLPRegressor(1, {"device": "cpu", "require_cuda": False, "epochs": 1, "batch_size": 8, "hidden_layers": [8]}).fit(x, y)
    prediction = model.predict(x[:2])
    assert prediction.shape == (2, 3)
    assert np.all((prediction >= 0) & (prediction <= 1))
