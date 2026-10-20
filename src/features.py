"""Features built from the incident table, and the split by date."""
import numpy as np
import pandas as pd

from src import config


def add_time_features(table):
    """Hour and weekday of the opening, as text so they are encoded like the other categories."""
    out = table.copy()
    out["hour"] = out["opened_at"].dt.hour.astype(str)
    out["weekday"] = out["opened_at"].dt.dayofweek.astype(str)   # 0 = Monday
    return out


def split_by_date(table, train_share=config.TRAIN_SHARE, val_share=config.VAL_SHARE):
    """Add a 'split' column (train / validation / test). The oldest incidents go to train."""
    cut_val = table["opened_at"].quantile(train_share)
    cut_test = table["opened_at"].quantile(train_share + val_share)
    split = np.select([table["opened_at"] < cut_val, table["opened_at"] < cut_test],
                      ["train", "validation"], default="test")
    return table.assign(split=split)


def load_table():
    """Incident table of notebook 03, with the time features and the split column."""
    table = pd.read_csv(config.INCIDENT_FILE, parse_dates=["opened_at", "closed_at"])
    return split_by_date(add_time_features(table))
