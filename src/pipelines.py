"""Preprocessing shared by all the models."""
from sklearn.compose import ColumnTransformer
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
