import numpy as np
import pytest

from src.training.train_models import CatBoostRegressor, PerOutputCatBoostRegressor


@pytest.mark.skipif(CatBoostRegressor is None, reason="CatBoost is optional")
def test_catboost_wrapper_accepts_constant_haptic_target():
    x = np.arange(24, dtype=float).reshape(12, 2)
    y = np.column_stack([np.linspace(0, 1, 12), np.zeros(12)])
    model = PerOutputCatBoostRegressor(seed=1).fit(x, y)
    prediction = model.predict(x[:2])
    assert prediction.shape == (2, 2)
    assert np.all(prediction[:, 1] == 0)
