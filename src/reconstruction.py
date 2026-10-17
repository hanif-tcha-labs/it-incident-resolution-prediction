"""Rebuild one row per incident from the event log.

Rules (details in notebook 03 and reports/reconstruction_rules.md):
- events are ordered by sys_updated_at, ties keep the file order
- the target uses the last resolution of the incident
- the features are the values of the first event, nothing is filled from later events
"""
import numpy as np
import pandas as pd

from src import config

ID = config.ID_COL


def sort_events(df):
    """Order the events of each incident by time. The sort is stable, so ties keep the file order."""
    return df.sort_values([ID, "sys_updated_at"], kind="stable")


def resolution_time(ev):
    """Time of the last resolution of each incident, and where it comes from.

    It is resolved_at when the column is filled. If not, it is the time of the
    last event in state 'Resolved'. Incidents that never reach 'Resolved' get NaT.
    `ev` must be sorted with sort_events().
    """
    resolved_at = ev.groupby(ID, sort=False)["resolved_at"].max()
    last_resolved_event = (ev[ev["incident_state"] == "Resolved"]
                           .groupby(ID)["sys_updated_at"].max()
                           .reindex(resolved_at.index))
    when = resolved_at.fillna(last_resolved_event)
    source = pd.Series(np.select(
        [resolved_at.notna(), last_resolved_event.notna()],
        ["resolved_at", "last Resolved event"],
        default="none"), index=resolved_at.index)
    return when, source


def build_incident_table(df):
    """One row per incident: target, features at opening, and columns for analysis only."""
    ev = sort_events(df)
    g = ev.groupby(ID, sort=False)
    first = g.head(1).set_index(ID)

    # opened_at never changes inside an incident (checked in notebook 02)
    out = pd.DataFrame({"opened_at": first["opened_at"]})

    when, source = resolution_time(ev)
    out[config.TARGET] = (when - out["opened_at"]).dt.total_seconds() / 3600
    out["target_source"] = source

    out[config.INITIAL_COLS] = first[config.INITIAL_COLS]

    out["first_event_state"] = first["incident_state"]
    out["n_events"] = g.size()
    out["reassignment_count"] = g["reassignment_count"].max()
    out["reopen_count"] = g["reopen_count"].max()
    out["closed_at"] = g["closed_at"].max()
    return out.reset_index()
