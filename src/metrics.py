"""Metrics, all in hours."""
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error


def regression_metrics(y_true, y_pred):
    """MAE, RMSE and RMSLE. Negative predictions are set to 0 because a duration can't be negative."""
    y_pred = np.clip(y_pred, 0, None)
    return {
        "MAE": mean_absolute_error(y_true, y_pred),
        "RMSE": np.sqrt(mean_squared_error(y_true, y_pred)),
        "RMSLE": np.sqrt(np.mean((np.log1p(y_true) - np.log1p(y_pred)) ** 2)),
    }
