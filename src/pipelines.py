"""Preprocessing shared by all the models, and the final pipeline."""
import numpy as np
from sklearn.compose import ColumnTransformer, TransformedTargetRegressor
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from src import config


def make_preprocessor(features=config.FEATURES, min_frequency=config.MIN_FREQUENCY):
    """One-hot encoding of the features.

    A missing value is its own level. Rare levels are grouped in one column,
    and a level never seen in the train set goes there too.
    """
    onehot = OneHotEncoder(handle_unknown="infrequent_if_exist", min_frequency=min_frequency,
                           sparse_output=False)
    return ColumnTransformer([("cat", onehot, list(features))])


def make_final_pipeline():
    """Final model (notebook 06): preprocessing + HistGradientBoosting trained on log(1 + hours).

    The predictions come back in hours.
    """
    model = HistGradientBoostingRegressor(early_stopping=False, random_state=config.RANDOM_STATE,
                                          **config.FINAL_MODEL_PARAMS)
    model = TransformedTargetRegressor(model, func=np.log1p, inverse_func=np.expm1)
    return Pipeline([("prep", make_preprocessor()), ("model", model)])
