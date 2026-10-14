"""Audit functions for the incident event log (one row = one event).

They return small tables or numbers. Nothing here drops a row.
"""
import pandas as pd

from src import config

ID = config.ID_COL


def first_last_events(df, id_col=ID):
    """First and last logged event of each incident (file order)."""
    g = df.groupby(id_col, sort=False)
    return g.head(1).set_index(id_col), g.tail(1).set_index(id_col)


# ---------------------------------------------------------------- granularity and order
def events_per_incident(df, id_col=ID):
    """Number of events of each incident."""
    return df.groupby(id_col, sort=False).size().rename("n_events")


def file_order_checks(df, id_col=ID):
    """How the file is sorted: by incident number, by opening date, and inside incidents."""
    g = df.groupby(id_col, sort=False)
    first_number = df[id_col].drop_duplicates().str.extract(r"(\d+)$")[0].astype("int64")
    return {
        "incident ids are in contiguous blocks": bool(df[id_col].ne(df[id_col].shift()).sum() == df[id_col].nunique()),
        "incident numbers increase through the file": bool(first_number.is_monotonic_increasing),
        "opened_at increases through the file (incident level)": bool(g["opened_at"].first().is_monotonic_increasing),
        "incidents where sys_updated_at goes backwards": int((~g["sys_updated_at"].apply(lambda s: s.is_monotonic_increasing)).sum()),
        "incidents where sys_mod_count is not increasing": int((~g["sys_mod_count"].apply(lambda s: s.is_monotonic_increasing)).sum()),
        "incidents with a repeated sys_mod_count": int(g["sys_mod_count"].apply(lambda s: s.duplicated().any()).sum()),
        "incidents whose first event has sys_mod_count != 0": int((g["sys_mod_count"].first() != 0).sum()),
    }


def last_incident(df, id_col=ID):
    """Events of the last incident of the file."""
    cols = ["incident_state", "active", "sys_mod_count", "sys_updated_at", "resolved_at", "closed_at"]
    return df.loc[df[id_col] == df[id_col].iloc[-1], cols]


def final_state_counts(df, id_col=ID):
    """State of the last event of each incident."""
    return df.groupby(id_col, sort=False)["incident_state"].last().value_counts()


# ---------------------------------------------------------------- missing values and duplicates
def missing_summary(df):
    """Missing count, % missing and number of distinct values for each column."""
    out = pd.DataFrame({
        "dtype": df.dtypes.astype(str),
        "n_missing": df.isna().sum(),
        "pct_missing": (df.isna().mean() * 100).round(2),
        "n_unique": df.nunique(),
    })
    return out.sort_values("pct_missing", ascending=False)


def incident_level_missing(df, id_col=ID):
    """% of incidents where a column is missing on all events, and on at least one event."""
    miss = df.drop(columns=id_col).isna().groupby(df[id_col], sort=False)
    return pd.DataFrame({
        "pct_incidents_all_events_missing": (miss.all().mean() * 100).round(2),
        "pct_incidents_some_events_missing": (miss.any().mean() * 100).round(2),
    })


def exact_duplicates(df):
    """Number of rows identical to an earlier row, and all the rows involved."""
    return int(df.duplicated().sum()), df[df.duplicated(keep=False)]


# ---------------------------------------------------------------- stability inside incidents
def column_stability(df, id_col=ID):
    """For each column, how often its value changes between the events of an incident.

    pct_any_change   : % of incidents with more than one distinct value (missing counts as a value)
    pct_value_change : same, but only with real values
    pct_missing_first / pct_missing_last : % missing on the first / last event
    """
    cols = [c for c in df.columns if c != id_col]
    g = df.groupby(id_col, sort=False)[cols]
    any_change = (g.nunique(dropna=False) > 1).mean() * 100
    value_change = (g.nunique(dropna=True) > 1).mean() * 100
    first, last = first_last_events(df, id_col)
    out = pd.DataFrame({
        "pct_any_change": any_change,
        "pct_value_change": value_change,
        "pct_missing_first": first[cols].isna().mean() * 100,
        "pct_missing_last": last[cols].isna().mean() * 100,
    }).round(2)
    out["n_incidents_changing"] = (any_change / 100 * df[id_col].nunique()).round().astype(int)
    return out.sort_values("pct_any_change")


# ---------------------------------------------------------------- dates
def date_pair_violations(df, pairs, id_col=ID):
    """For each (early, late) pair of date columns, count the rows where early > late."""
    n_incidents = df[id_col].nunique()
    rows = []
    for early, late in pairs:
        both = df[early].notna() & df[late].notna()
        bad = both & (df[early] > df[late])
        n_bad = df.loc[bad, id_col].nunique()
        rows.append({
            "check": f"{early} > {late}",
            "rows_compared": int(both.sum()),
            "n_events": int(bad.sum()),
            "n_incidents": int(n_bad),
            "pct_incidents": round(n_bad / n_incidents * 100, 3),
        })
    return pd.DataFrame(rows)


def date_ranges(df, date_cols=config.DATE_COLS):
    """First and last value of each date column."""
    return pd.DataFrame({"min": df[date_cols].min(), "max": df[date_cols].max()})


# ---------------------------------------------------------------- resolution
def resolution_diagnostic(df, id_col=ID):
    """One row per incident, to study how resolved_at, the 'Resolved' state and the reopenings fit together.

    This is not the final incident table, it is only used for the audit.
    """
    ev = df.sort_values([id_col, "sys_updated_at"], kind="stable")
    g = ev.groupby(id_col, sort=False)
    is_resolved = ev["incident_state"] == "Resolved"
    # a "phase" starts when the state becomes Resolved after another state
    phase_start = is_resolved & ~is_resolved.groupby(ev[id_col]).shift(fill_value=False)
    out = pd.DataFrame({
        "n_events": g.size(),
        "opened_at": g["opened_at"].first(),
        "n_distinct_resolved_at": g["resolved_at"].nunique(),
        "resolved_at": g["resolved_at"].max(),
        "closed_at": g["closed_at"].max(),
        "max_reopen_count": g["reopen_count"].max(),
        "n_resolved_phases": phase_start.groupby(ev[id_col]).sum(),
        "first_event_state": g["incident_state"].first(),
        "last_event_state": g["incident_state"].last(),
        "final_priority": g["priority"].last(),
    })
    out["last_resolved_event_at"] = ev[is_resolved].groupby(id_col)["sys_updated_at"].max()
    out["has_resolved_at"] = out["resolved_at"].notna()
    out["has_resolved_state"] = out["last_resolved_event_at"].notna()
    return out


# ---------------------------------------------------------------- rare categories
def rare_categories(df, col, min_incidents, id_col=ID):
    """Values of `col` found in fewer than `min_incidents` incidents."""
    counts = (
        df.dropna(subset=[col]).groupby(col)
        .agg(n_events=(id_col, "size"), n_incidents=(id_col, "nunique"))
        .sort_values("n_incidents")
    )
    return counts[counts["n_incidents"] < min_incidents]


def cardinality_table(df, cols, min_incidents, id_col=ID):
    """Number of distinct values and of rare values for each column."""
    rows = []
    for c in cols:
        rare = rare_categories(df, c, min_incidents, id_col)
        rows.append({
            "column": c,
            "n_unique": df[c].nunique(),
            "n_rare_values": len(rare),
            "incidents_with_rare_value": int(df[df[c].isin(rare.index)][id_col].nunique()),
        })
    return pd.DataFrame(rows).set_index("column")
