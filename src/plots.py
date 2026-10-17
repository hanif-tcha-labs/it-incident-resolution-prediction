"""Simple plots for the audit. Each function saves a PNG in reports/figures/."""
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
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


def plot_target_by_group(table, group_col, target_col, name="target_by_group"):
    """Histogram of log10(1 + hours) for each group, each group with its own density."""
    data = table.assign(log_hours=np.log10(1 + table[target_col]))
    fig, ax = plt.subplots(figsize=(8, 3.8))
    sns.histplot(data=data, x="log_hours", hue=group_col, stat="density", common_norm=False,
                 bins=40, element="step", ax=ax)
    ax.set_xlabel("log10(1 + resolution time in hours)")
    ax.set_title("Resolution time by group")
    save_fig(fig, name)


# ---------------------------------------------------------------- EDA (notebook 04)
def plot_target_distribution(target, name="target_distribution"):
    """Resolution time: normal scale up to the 95th percentile, and log scale for everything."""
    cut = target.quantile(0.95)
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.8))
    axes[0].hist(target[target <= cut], bins=50, color="#4C72B0", edgecolor="white")
    axes[0].set_title(f"Up to the 95th percentile ({cut:.0f} h)")
    axes[0].set_xlabel("Resolution time (hours)")
    axes[0].set_ylabel("Incidents")
    axes[1].hist(np.log10(1 + target), bins=50, color="#4C72B0", edgecolor="white")
    axes[1].set_title("All incidents, log scale")
    axes[1].set_xlabel("log10(1 + resolution time in hours)")
    save_fig(fig, name)


def plot_box_by_group(table, col, target_col, order=None, name=None):
    """Boxplot of log10(1 + hours) for each value of `col`."""
    data = table.assign(log_hours=np.log10(1 + table[target_col]))
    fig, ax = plt.subplots(figsize=(8, 3.8))
    sns.boxplot(data=data, x=col, y="log_hours", order=order, color="#8DA0CB", ax=ax)
    ax.set_ylabel("log10(1 + resolution time in hours)")
    ax.set_title(f"Resolution time by {col}")
    ax.tick_params(axis="x", rotation=30)
    save_fig(fig, name or f"box_by_{col}")


def plot_median_by_time(table, target_col, name="median_target_by_opening_time"):
    """Median resolution time by hour, weekday and month of opening."""
    opened = table["opened_at"]
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    panels = [
        ("Hour of opening", table.groupby(opened.dt.hour)[target_col].median()),
        ("Weekday", table.groupby(opened.dt.day_name())[target_col].median().reindex(days)),
        ("Month", table.groupby(opened.dt.to_period("M").astype(str))[target_col].median()),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.6))
    for ax, (title, s) in zip(axes, panels):
        ax.bar(s.index.astype(str), s.values, color="#4C72B0")
        ax.set_title(title)
        ax.set_ylabel("Median resolution time (h)")
        ax.tick_params(axis="x", rotation=60)
    save_fig(fig, name)
