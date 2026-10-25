"""Tests verifying artifact presence, schemas, and numeric reference invariants."""
import json
from pathlib import Path
import pandas as pd
import pytest

from app import config

ARTIFACTS_DIR = config.ARTIFACTS_DIR


def test_required_artifacts_exist():
    """All required model, metric, eda, and replay artifacts must be present."""
    required = [
        "model/final_pipeline.joblib",
        "model/model_card.json",
        "metrics/data_summary.json",
        "metrics/data_dictionary.json",
        "metrics/features.json",
        "metrics/split.json",
        "metrics/weekly_target.json",
        "metrics/model_comparison.json",
        "metrics/tuning_results.json",
        "metrics/sensitivity_checks.json",
        "metrics/final_test_metrics.json",
        "metrics/errors_by_group.json",
        "metrics/permutation_importance.json",
        "metrics/weekly_errors_test.json",
        "metrics/prediction_ranges.json",
        "eda/target_distribution.json",
        "eda/by_group.json",
        "options.json",
        "replay/test_incidents.csv",
    ]
    for rel_path in required:
        p = ARTIFACTS_DIR / rel_path
        assert p.exists(), f"Missing required artifact: {rel_path}"
        assert p.stat().st_size > 0, f"Artifact is empty: {rel_path}"


def test_data_summary_invariants():
    """Raw counts and incident reconstruction counts must strictly match project specifications."""
    with open(ARTIFACTS_DIR / "metrics/data_summary.json", "r", encoding="utf-8") as f:
        summary = json.load(f)

    assert summary["n_events"] == 141712, "Must contain exactly 141,712 events"
    assert summary["n_incidents"] == 24918, "Must contain exactly 24,918 raw incidents"
    assert summary["n_with_target"] == 24905, "Must contain exactly 24,905 incidents with target"
    assert summary["n_without_target"] == 13, "Must contain exactly 13 unresolved incidents without target"
    assert summary["exact_duplicates"] == 0, "Log contains zero exact duplicate rows"


def test_split_invariants():
    """Temporal split must be partitioned into 60% train, 20% validation, 20% test."""
    with open(ARTIFACTS_DIR / "metrics/split.json", "r", encoding="utf-8") as f:
        split = json.load(f)

    assert split["train"]["n"] == 14943, "Train split must be 14,943"
    assert split["validation"]["n"] == 4981, "Validation split must be 4,981"
    assert split["test"]["n"] == 4981, "Test split must be 4,981"


def test_model_metrics_invariants():
    """Final test metrics must match validated reference values (MAE ~117.24 h, baseline ~132.49 h)."""
    with open(ARTIFACTS_DIR / "metrics/final_test_metrics.json", "r", encoding="utf-8") as f:
        metrics_data = json.load(f)

    model_mae = metrics_data["model"]["MAE"]
    baseline_mae = metrics_data["baseline"]["MAE"]

    assert abs(model_mae - 117.24) <= 0.05, f"Model test MAE {model_mae} diverges from 117.24"
    assert abs(baseline_mae - 132.49) <= 0.05, f"Baseline test MAE {baseline_mae} diverges from 132.49"


def test_replay_file_invariants():
    """Replay CSV must have exactly 4,981 test rows, sorted by opened_at, and NO predictions."""
    df = pd.read_csv(ARTIFACTS_DIR / "replay/test_incidents.csv")
    assert len(df) == 4981, "Replay file must contain 4,981 test incidents"

    # Verify no prediction columns leaked into replay file
    for col in df.columns:
        assert "pred" not in col.lower(), f"Replay CSV must NOT contain prediction column: {col}"

    # Verify sorted chronologically
    opened = pd.to_datetime(df["opened_at"])
    assert opened.is_monotonic_increasing, "Replay CSV must be sorted chronologically by opened_at"
