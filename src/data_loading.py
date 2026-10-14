"""Read the raw event log, apply the types and save the typed copy."""
import pandas as pd

from src import config


def read_raw_text(path=config.RAW_FILE):
    """Read the raw file with every column as text and no missing-value conversion.

    Used to look at the file exactly as it is (for example to count the '?').
    """
    return pd.read_csv(path, sep=config.CSV_SEPARATOR, dtype=str, keep_default_na=False)


def parse_dates(series, fmt=config.DATE_FORMAT):
    """Convert a text column to datetime with an explicit format.

    A value that does not match the format raises an error, so a bad date
    is never turned into NaT silently.
    """
    parsed = pd.to_datetime(series, format=fmt, errors="coerce")
    failed = parsed.isna() & series.notna()
    if failed.any():
        examples = series[failed].unique()[:5].tolist()
        raise ValueError(f"{failed.sum()} values of '{series.name}' do not match {fmt}: {examples}")
    return parsed


def to_bool(series):
    """Convert 'True'/'False' text (any case) to bool. Other values raise an error."""
    out = series.str.strip().str.lower().map({"true": True, "false": False})
    unknown = out.isna()
    if unknown.any():
        raise ValueError(f"Unexpected values in '{series.name}': {series[unknown].unique()[:5].tolist()}")
    return out.astype(bool)


def load_raw(path=config.RAW_FILE):
    """Load the event log with '?' as NaN and the right types. No row is dropped."""
    df = pd.read_csv(path, sep=config.CSV_SEPARATOR, dtype=str,
                     na_values=config.MISSING_MARKERS, keep_default_na=False)
    for col in config.DATE_COLS:
        df[col] = parse_dates(df[col])
    for col in config.BOOL_COLS:
        df[col] = to_bool(df[col])
    for col in config.INT_COLS:
        df[col] = pd.to_numeric(df[col]).astype("int64")
    return df


def save_typed(df, path=config.INTERIM_FILE):
    """Save the typed event log as CSV, with dates in ISO format."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, date_format="%Y-%m-%d %H:%M:%S")
    return path
