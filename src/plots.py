"""Simple plots for the audit. Each function saves a PNG in reports/figures/."""
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import seaborn as sns

from src import config

sns.set_theme(style="whitegrid", context="notebook")


def save_fig(fig, name):
    """Save a figure in reports/figures/."""
    config.FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(config.FIGURES_DIR / f"{name}.png", dpi=130, bbox_inches="tight")


def plot_incidents_per_week(opened_at, name="incidents_opened_per_week"):
    """Bars of the number of incidents opened each week."""
    per_week = opened_at.dt.to_period("W").value_counts().sort_index()
    per_week.index = per_week.index.start_time
    fig, ax = plt.subplots(figsize=(10, 3.5))
    ax.bar(per_week.index, per_week.values, width=6, color="#4C72B0")
    ax.set_title("Incidents opened per week")
    ax.set_xlabel("Week of opening")
    ax.set_ylabel("Incidents")
    ax.xaxis.set_major_locator(mdates.MonthLocator())   # one tick per month
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))
    ax.tick_params(axis="x", rotation=45)
    save_fig(fig, name)


def plot_events_per_incident(n_events, name="events_per_incident"):
    """Histogram of the number of events per incident, normal and log scale."""
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.8))
    for ax, log in zip(axes, [False, True]):
        ax.hist(n_events, bins=range(1, int(n_events.max()) + 2), color="#4C72B0", edgecolor="white")
        ax.set_xlabel("Events per incident")
        ax.set_ylabel("Incidents (log scale)" if log else "Incidents")
        if log:
            ax.set_yscale("log")
    axes[0].set_title("Events per incident")
    axes[1].set_title("Same, log scale")
    save_fig(fig, name)


def plot_missing(summary, name="missing_values_by_column"):
    """Bars of the % of missing values for the columns that have some."""
    data = summary[summary["pct_missing"] > 0].sort_values("pct_missing")
    fig, ax = plt.subplots(figsize=(8, 0.32 * len(data) + 1.2))
    ax.barh(data.index, data["pct_missing"], color="#C44E52")
    ax.set_xlabel("% of events missing")
    ax.set_title("Missing values by column")
    ax.set_xlim(0, 100)
    save_fig(fig, name)


def plot_stability(stability, name="column_stability_in_incident"):
    """Bars of the % of incidents where each column changes between events."""
    data = stability.sort_values("pct_any_change")
    fig, ax = plt.subplots(figsize=(8, 0.32 * len(data) + 1.2))
    ax.barh(data.index, data["pct_any_change"], color="#55A868")
    ax.set_xlabel("% of incidents where the value changes between events")
    ax.set_title("Stability of each column inside an incident")
    ax.set_xlim(0, 100)
    save_fig(fig, name)


def plot_missing_resolution_by_priority(table, name="missing_resolved_at_by_priority"):
    """Bars of the % of incidents without resolved_at, for each priority."""
    fig, ax = plt.subplots(figsize=(6.5, 3.5))
    ax.bar(table.index, table["pct_missing"], color="#8172B2")
    ax.set_ylabel("% incidents without resolved_at")
    ax.set_xlabel("Final priority")
    ax.set_title("Missing resolved_at by priority")
    save_fig(fig, name)
