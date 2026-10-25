"""Export project artifacts from the training pipeline and verified reports.

Usage:
    python -m src.export_artifacts
"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.inspection import permutation_importance

from src import config, data_loading, features, metrics, pipelines, reconstruction

# Avoid loky warning on Windows if CPU core query fails
os.environ["LOKY_MAX_CPU_COUNT"] = "4"

ARTIFACTS_DIR = config.PROJECT_ROOT / "artifacts"
MODEL_DIR = ARTIFACTS_DIR / "model"
METRICS_DIR = ARTIFACTS_DIR / "metrics"
EDA_DIR = ARTIFACTS_DIR / "eda"
REPLAY_DIR = ARTIFACTS_DIR / "replay"


def ensure_directories():
    """Create all destination directories under artifacts/."""
    for d in [MODEL_DIR, METRICS_DIR, EDA_DIR, REPLAY_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def validate_export_inputs():
    """Fail early with setup guidance when notebook-generated inputs are missing."""
    required_inputs = [
        ("source event log", config.RAW_FILE),
        ("reconstructed incident table (notebook 03)", config.INCIDENT_FILE),
        ("unresolved incident table (notebook 03)", config.NO_TARGET_FILE),
        ("validation model comparison (notebook 05)", config.TABLES_DIR / "model_comparison_validation.csv"),
        ("tuned model comparison (notebook 06)", config.TABLES_DIR / "model_comparison_tuned.csv"),
    ]
    missing = [(description, path) for description, path in required_inputs if not path.is_file()]
    if not missing:
        return

    missing_files = "\n".join(f"- {description}: {path}" for description, path in missing)
    raise FileNotFoundError(
        "Cannot rebuild model artifacts because required input files are missing:\n"
        f"{missing_files}\n"
        "The export command does not create these source and notebook outputs. "
        "Provide data/raw/incident_event_log.csv, then run notebooks 03, 05, and 06 "
        "in order before retrying. To run the application with the committed model, "
        "you do not need to run this export command."
    )


def export_raw_and_summary():
    """Verify raw log counts and export data summary and dictionary."""
    print("1/7 Checking raw data and generating summaries...")
    raw_df = pd.read_csv(config.RAW_FILE, sep=config.CSV_SEPARATOR, dtype=str, keep_default_na=False)
    n_events, n_cols = raw_df.shape
    n_unique_incidents = raw_df[config.ID_COL].nunique()

    # Raw counts assertion
    assert n_events == 141712, f"Expected 141712 events, got {n_events}"
    assert n_unique_incidents == 24918, f"Expected 24918 incidents, got {n_unique_incidents}"
    assert n_cols == 36, f"Expected 36 columns, got {n_cols}"

    # Missing values count ('?')
    missing_counts = {}
    for col in raw_df.columns:
        cnt = int((raw_df[col] == "?").sum())
        missing_counts[col] = {
            "missing_events": cnt,
            "pct_missing": round(cnt / n_events * 100, 2),
        }

    # Incident table counts
    inc_table = pd.read_csv(config.INCIDENT_FILE)
    n_with_target = len(inc_table)
    assert n_with_target == 24905, f"Expected 24905 with target, got {n_with_target}"

    no_target_df = pd.read_csv(config.NO_TARGET_FILE)
    n_without_target = len(no_target_df)
    assert n_without_target == 13, f"Expected 13 without target, got {n_without_target}"

    n_created_resolved = int((inc_table["first_event_state"] == "Resolved").sum())
    n_reopened = int((inc_table["reopen_count"] > 0).sum())

    data_summary = {
        "n_events": n_events,
        "n_incidents": n_unique_incidents,
        "n_columns": n_cols,
        "n_with_target": n_with_target,
        "n_without_target": n_without_target,
        "n_created_resolved": n_created_resolved,
        "pct_created_resolved": round(n_created_resolved / n_with_target * 100, 2),
        "n_reopened": n_reopened,
        "pct_reopened": round(n_reopened / n_with_target * 100, 2),
        "exact_duplicates": 0,
        "missing_by_column": missing_counts,
    }
    with open(METRICS_DIR / "data_summary.json", "w", encoding="utf-8") as f:
        json.dump(data_summary, f, indent=2)

    # Data dictionary from config
    dictionary = []
    for col, (group, meaning) in config.COLUMN_INFO.items():
        avail, reason, planned_use = config.AVAILABILITY.get(
            col, ("unknown", "No availability documented", "")
        )
        is_used = col in config.FEATURES or col == config.TARGET
        dictionary.append({
            "column": col,
            "group": group,
            "meaning": meaning,
            "availability": avail,
            "reason": reason,
            "used_as_feature": col in config.FEATURES,
            "is_target": col == config.TARGET,
            "planned_use": planned_use,
        })
    with open(METRICS_DIR / "data_dictionary.json", "w", encoding="utf-8") as f:
        json.dump(dictionary, f, indent=2)

    # Features and exclusions
    features_info = {
        "features": config.FEATURES,
        "min_frequency": config.MIN_FREQUENCY,
        "target": config.TARGET,
        "excluded": [
            {"column": "caller_id", "reason": "Too many rare categories (high cardinality)."},
            {"column": "notify", "reason": "Almost constant across incidents."},
            {"column": "cmdb_ci", "reason": "99.7% missing values."},
            {"column": "sys_created_at", "reason": "Redundant, nearly identical to opened_at."},
            {"column": "incident_state", "reason": "Known only after opening (data leakage)."},
            {"column": "active", "reason": "Known only after opening (data leakage)."},
            {"column": "reassignment_count", "reason": "Increases during resolution process (leakage)."},
            {"column": "reopen_count", "reason": "Increases after first resolution (leakage)."},
            {"column": "sys_mod_count", "reason": "Event counter during incident handling (leakage)."},
            {"column": "made_sla", "reason": "Process outcome directly tied to resolution time."},
            {"column": "assigned_to", "reason": "Assigned during handling, often empty at opening."},
            {"column": "knowledge", "reason": "Flagged when article used during resolution."},
            {"column": "u_priority_confirmation", "reason": "Confirmed during handling."},
            {"column": "problem_id", "reason": "Linked problem record attached later."},
            {"column": "rfc", "reason": "Change request attached later."},
            {"column": "vendor", "reason": "Vendor assigned later."},
            {"column": "caused_by", "reason": "Identified after root cause analysis."},
            {"column": "closed_code", "reason": "Closure code set at resolution."},
            {"column": "resolved_by", "reason": "Staff member who resolved the ticket."},
            {"column": "resolved_at", "reason": "End timestamp of resolution target."},
            {"column": "closed_at", "reason": "Administrative closure timestamp."},
        ],
    }
    with open(METRICS_DIR / "features.json", "w", encoding="utf-8") as f:
        json.dump(features_info, f, indent=2)


def export_eda_and_splits(table):
    """Export EDA distributions, weekly target stats, and split metadata."""
    print("2/7 Exporting EDA distributions and split information...")
    target = table[config.TARGET]

    # Split assertions and summary
    train = table[table["split"] == "train"]
    val = table[table["split"] == "validation"]
    test = table[table["split"] == "test"]

    assert len(train) == 14943, f"Expected 14943 train, got {len(train)}"
    assert len(val) == 4981, f"Expected 4981 val, got {len(val)}"
    assert len(test) == 4981, f"Expected 4981 test, got {len(test)}"

    split_info = {}
    for name, subset in [("train", train), ("validation", val), ("test", test)]:
        t = subset[config.TARGET]
        split_info[name] = {
            "n": len(subset),
            "pct": round(len(subset) / len(table) * 100, 2),
            "first_opened": str(subset["opened_at"].min()),
            "last_opened": str(subset["opened_at"].max()),
            "median": round(float(t.median()), 2),
            "mean": round(float(t.mean()), 2),
            "p90": round(float(t.quantile(0.9)), 2),
            "pct_created_resolved": round(float((subset["first_event_state"] == "Resolved").mean() * 100), 2),
        }
    with open(METRICS_DIR / "split.json", "w", encoding="utf-8") as f:
        json.dump(split_info, f, indent=2)

    # Weekly target across all incidents
    weekly_agg = table.groupby(table["opened_at"].dt.to_period("W"))[config.TARGET].agg(
        n="size",
        median="median",
        p90=lambda s: s.quantile(0.9),
    ).reset_index()

    weekly_target = []
    for _, row in weekly_agg.iterrows():
        weekly_target.append({
            "week": str(row["opened_at"]),
            "n": int(row["n"]),
            "median": round(float(row["median"]), 2),
            "p90": round(float(row["p90"]), 2),
        })
    with open(METRICS_DIR / "weekly_target.json", "w", encoding="utf-8") as f:
        json.dump(weekly_target, f, indent=2)

    # EDA: Target distribution and percentiles
    percentiles = [0.01, 0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99]
    perc_values = {f"p{int(p*100)}": round(float(target.quantile(p)), 2) for p in percentiles}
    shares = {
        "exactly_0h": round(float(target.eq(0).mean() * 100), 2),
        "under_1h": round(float(target.lt(1).mean() * 100), 2),
        "under_24h": round(float(target.lt(24).mean() * 100), 2),
        "over_7d": round(float(target.gt(168).mean() * 100), 2),
        "over_30d": round(float(target.gt(720).mean() * 100), 2),
    }

    # Log10 histogram bins for visualization
    log_vals = np.log10(1 + target)
    hist_counts, bin_edges = np.histogram(log_vals, bins=40)
    log_histogram = [
        {
            "bin_start": round(float(bin_edges[i]), 3),
            "bin_end": round(float(bin_edges[i + 1]), 3),
            "count": int(hist_counts[i]),
        }
        for i in range(len(hist_counts))
    ]

    target_dist = {
        "count": len(target),
        "mean": round(float(target.mean()), 2),
        "std": round(float(target.std()), 2),
        "min": round(float(target.min()), 2),
        "max": round(float(target.max()), 2),
        "skewness": round(float(target.skew()), 2),
        "log1p_skewness": round(float(np.log1p(target).skew()), 2),
        "percentiles": perc_values,
        "shares": shares,
        "log_histogram": log_histogram,
    }
    with open(EDA_DIR / "target_distribution.json", "w", encoding="utf-8") as f:
        json.dump(target_dist, f, indent=2)

    # EDA: Target by group
    table_eda = table.copy()
    table_eda["month"] = table_eda["opened_at"].dt.to_period("M").astype(str)

    groups_to_study = ["priority", "impact", "urgency", "category", "contact_type",
                       "assignment_group", "weekday", "hour", "month"]
    by_group_dict = {}
    for col in groups_to_study:
        g = table_eda.groupby(col, observed=True, dropna=False)[config.TARGET].agg(
            n="size",
            median="median",
            mean="mean",
            p90=lambda s: s.quantile(0.9),
        ).reset_index()
        # Sort by n descending, or order naturally for priority/weekday/hour/month
        if col in ["priority", "impact", "urgency", "weekday", "hour", "month"]:
            g = g.sort_values(col)
        else:
            g = g.sort_values("n", ascending=False)
        by_group_dict[col] = [
            {
                "category": str(r[col]) if pd.notna(r[col]) else "Missing",
                "n": int(r["n"]),
                "median": round(float(r["median"]), 2),
                "mean": round(float(r["mean"]), 2),
                "p90": round(float(r["p90"]), 2),
            }
            for _, r in g.iterrows()
        ]
    with open(EDA_DIR / "by_group.json", "w", encoding="utf-8") as f:
        json.dump(by_group_dict, f, indent=2)


def train_and_export_model(table):
    """Train the final pipeline on train+val and export model and card."""
    print("3/7 Training final pipeline on train+val and saving model...")
    train = table[table["split"] == "train"]
    val = table[table["split"] == "validation"]
    test = table[table["split"] == "test"]
    train_val = pd.concat([train, val], ignore_index=True)

    pipeline = pipelines.make_final_pipeline()
    pipeline.fit(train_val[config.FEATURES], train_val[config.TARGET])

    # Save fitted pipeline
    joblib.dump(pipeline, MODEL_DIR / "final_pipeline.joblib")

    # Predict test set and baseline
    y_test = test[config.TARGET].to_numpy()
    pred = np.clip(pipeline.predict(test[config.FEATURES]), 0, None)
    base_pred = np.full(len(test), train_val[config.TARGET].median())

    m_model = metrics.regression_metrics(y_test, pred)
    m_base = metrics.regression_metrics(y_test, base_pred)

    print(f"Model test MAE: {m_model['MAE']:.2f} (Target: ~117.24)")
    print(f"Baseline test MAE: {m_base['MAE']:.2f} (Target: ~132.49)")

    assert abs(m_model["MAE"] - 117.24) <= 0.05, f"Model MAE {m_model['MAE']} deviates from 117.24"
    assert abs(m_base["MAE"] - 132.49) <= 0.05, f"Baseline MAE {m_base['MAE']} deviates from 132.49"

    # Export model card
    model_card = {
        "model_name": "HistGradientBoostingRegressor",
        "pipeline_structure": "ColumnTransformer(OneHotEncoder) -> TransformedTargetRegressor(HistGradientBoostingRegressor)",
        "versions": {
            "python": sys.version.split()[0],
            "scikit_learn": sklearn.__version__,
            "pandas": pd.__version__,
            "numpy": np.__version__,
            "joblib": joblib.__version__,
        },
        "training_date": datetime.now().isoformat(),
        "n_train_validation": len(train_val),
        "n_test": len(test),
        "target": config.TARGET,
        "target_transform": "log1p",
        "features": config.FEATURES,
        "min_frequency": config.MIN_FREQUENCY,
        "hyperparameters": config.FINAL_MODEL_PARAMS,
        "split_strategy": "Temporal split: oldest 60% train, next 20% validation, last 20% test",
        "test_metrics": {
            "model": {k: round(float(v), 2) for k, v in m_model.items()},
            "baseline": {k: round(float(v), 2) for k, v in m_base.items()},
        },
    }
    with open(MODEL_DIR / "model_card.json", "w", encoding="utf-8") as f:
        json.dump(model_card, f, indent=2)

    return pipeline, train_val, test, y_test, pred, base_pred


def export_test_evaluations(pipeline, train_val, test, y_test, pred, base_pred):
    """Compute and export bootstrap intervals, error breakdowns, and permutation importance."""
    print("4/7 Computing test metrics, bootstrap intervals, and error breakdowns...")
    err_model = np.abs(y_test - pred)
    err_base = np.abs(y_test - base_pred)

    # 1000 bootstrap iterations
    rng = np.random.default_rng(config.RANDOM_STATE)
    idx = rng.integers(0, len(test), (1000, len(test)))
    mae_model_boot = err_model[idx].mean(axis=1)
    gain_boot = err_base[idx].mean(axis=1) - mae_model_boot

    mae_ci = [round(float(x), 2) for x in np.percentile(mae_model_boot, [2.5, 97.5])]
    gain_ci = [round(float(x), 2) for x in np.percentile(gain_boot, [2.5, 97.5])]

    resid = pred - y_test
    over_estimated_pct = round(float((resid > 0).mean() * 100), 2)
    mean_error = round(float(resid.mean()), 2)
    median_error = round(float(np.median(resid)), 2)

    final_metrics = {
        "baseline": {
            "MAE": round(float(metrics.regression_metrics(y_test, base_pred)["MAE"]), 2),
            "RMSE": round(float(metrics.regression_metrics(y_test, base_pred)["RMSE"]), 2),
            "RMSLE": round(float(metrics.regression_metrics(y_test, base_pred)["RMSLE"]), 2),
            "mean_error": round(float((base_pred - y_test).mean()), 2),
        },
        "model": {
            "MAE": round(float(metrics.regression_metrics(y_test, pred)["MAE"]), 2),
            "RMSE": round(float(metrics.regression_metrics(y_test, pred)["RMSE"]), 2),
            "RMSLE": round(float(metrics.regression_metrics(y_test, pred)["RMSLE"]), 2),
            "mean_error": mean_error,
        },
        "bootstrap": {
            "iterations": 1000,
            "confidence_level": 0.95,
            "mae_model_ci": mae_ci,
            "mae_reduction_ci": gain_ci,
        },
        "error_distribution": {
            "over_estimated_pct": over_estimated_pct,
            "mean_error": mean_error,
            "median_error": median_error,
        },
    }
    with open(METRICS_DIR / "final_test_metrics.json", "w", encoding="utf-8") as f:
        json.dump(final_metrics, f, indent=2)

    # Errors by group (duration, priority, category)
    def compute_error_table(group_series, name):
        d = pd.DataFrame({
            "group": group_series.reset_index(drop=True),
            "base_err": err_base,
            "model_err": err_model,
            "err": resid,
        })
        g = d.groupby("group", observed=True).agg(
            n=("model_err", "size"),
            MAE_baseline=("base_err", "mean"),
            MAE_model=("model_err", "mean"),
            mean_error=("err", "mean"),
        ).reset_index()
        total_model_err = err_model.sum()
        out = []
        for _, r in g.iterrows():
            grp_err = err_model[d["group"] == r["group"]].sum()
            out.append({
                name: str(r["group"]),
                "n": int(r["n"]),
                "pct_test": round(r["n"] / len(test) * 100, 2),
                "MAE_baseline": round(float(r["MAE_baseline"]), 2),
                "MAE_model": round(float(r["MAE_model"]), 2),
                "mean_error": round(float(r["mean_error"]), 2),
                "pct_of_total_error": round(float(grp_err / total_model_err * 100), 2),
            })
        return out

    duration_series = pd.cut(
        test[config.TARGET], [-0.1, 1, 24, np.inf], labels=["under 1 h", "1 to 24 h", "over 24 h"]
    )
    errors_by_group = {
        "by_duration": compute_error_table(duration_series, "duration"),
        "by_priority": compute_error_table(test["priority"], "priority"),
        "by_category": compute_error_table(test["category"], "category"),
    }
    with open(METRICS_DIR / "errors_by_group.json", "w", encoding="utf-8") as f:
        json.dump(errors_by_group, f, indent=2)

    # Weekly test errors
    test_copy = test.copy()
    test_copy["week"] = test_copy["opened_at"].dt.to_period("W").astype(str)
    test_copy["err_base"] = err_base
    test_copy["err_model"] = err_model
    test_copy["signed_err"] = resid

    weekly_test = test_copy.groupby("week").agg(
        n=("err_model", "size"),
        MAE_baseline=("err_base", "mean"),
        MAE_model=("err_model", "mean"),
        mean_error=("signed_err", "mean"),
    ).reset_index()

    weekly_test_list = [
        {
            "week": r["week"],
            "n": int(r["n"]),
            "MAE_baseline": round(float(r["MAE_baseline"]), 2),
            "MAE_model": round(float(r["MAE_model"]), 2),
            "mean_error": round(float(r["mean_error"]), 2),
        }
        for _, r in weekly_test.iterrows()
    ]
    with open(METRICS_DIR / "weekly_errors_test.json", "w", encoding="utf-8") as f:
        json.dump(weekly_test_list, f, indent=2)

    # Permutation importance on test set
    print("5/7 Computing permutation importance...")
    imp = permutation_importance(
        pipeline, test[config.FEATURES], y_test,
        scoring="neg_mean_absolute_error",
        n_repeats=5, random_state=config.RANDOM_STATE, n_jobs=-1
    )
    importance_list = [
        {
            "feature": feat,
            "mean": round(float(imp.importances_mean[i]), 3),
            "std": round(float(imp.importances_std[i]), 3),
        }
        for i, feat in enumerate(config.FEATURES)
    ]
    importance_list.sort(key=lambda x: x["mean"], reverse=True)

    # Grouped importance (priority+impact+urgency, hour+weekday)
    def shuffle_group(cols, repeats=5):
        reference = metrics.mean_absolute_error(y_test, pred)
        scores = []
        for _ in range(repeats):
            X = test[config.FEATURES].copy()
            X[cols] = X[cols].iloc[rng.permutation(len(X))].to_numpy()
            scores.append(metrics.mean_absolute_error(y_test, np.clip(pipeline.predict(X), 0, None)) - reference)
        return round(float(np.mean(scores)), 2)

    grouped_importance = {
        "priority_impact_urgency": shuffle_group(["priority", "impact", "urgency"]),
        "hour_weekday": shuffle_group(["hour", "weekday"]),
    }

    perm_dict = {
        "individual": importance_list,
        "grouped": grouped_importance,
        "interpretation": "assignment_group is the strongest predictor, followed by sys_created_by and category. Priority/impact/urgency provide almost zero predictive value once other factors are accounted for.",
    }
    with open(METRICS_DIR / "permutation_importance.json", "w", encoding="utf-8") as f:
        json.dump(perm_dict, f, indent=2)


def export_prediction_ranges(test, y_test, pred):
    """Compute empirical 80% duration intervals on test set grouped by predicted duration."""
    print("6/7 Computing empirical prediction ranges on test set...")
    bins = [-0.1, 1.0, 10.0, 50.0, 200.0, np.inf]
    labels = ["<1h", "1-10h", "10-50h", "50-200h", ">200h"]
    pred_bins = pd.cut(pred, bins=bins, labels=labels)

    df_ranges = pd.DataFrame({
        "pred_bin": pred_bins,
        "pred": pred,
        "actual": y_test,
    })

    grouped = df_ranges.groupby("pred_bin", observed=False).agg(
        n=("pred", "size"),
        q10=("actual", lambda s: s.quantile(0.1)),
        q50=("actual", lambda s: s.quantile(0.5)),
        q90=("actual", lambda s: s.quantile(0.9)),
        pct_over_24h=("actual", lambda s: (s > 24).mean() * 100),
    ).reset_index()

    ranges_list = []
    min_max_bounds = [
        (0.0, 1.0),
        (1.0, 10.0),
        (10.0, 50.0),
        (50.0, 200.0),
        (200.0, None),
    ]
    for i, r in grouped.iterrows():
        b_min, b_max = min_max_bounds[i]
        ranges_list.append({
            "bin": str(r["pred_bin"]),
            "min_pred_hours": b_min,
            "max_pred_hours": b_max,
            "n_test_samples": int(r["n"]),
            "q10_hours": round(float(r["q10"]), 2),
            "q50_hours": round(float(r["q50"]), 2),
            "q90_hours": round(float(r["q90"]), 2),
            "pct_over_24h": round(float(r["pct_over_24h"]), 2),
            "interpretation": f"Among test incidents with predicted duration in this range ({r['n']} cases), 80% resolved between {r['q10']:.2f} h and {r['q90']:.2f} h.",
        })

    with open(METRICS_DIR / "prediction_ranges.json", "w", encoding="utf-8") as f:
        json.dump(ranges_list, f, indent=2)


def export_options_and_replay(table, train_val, test):
    """Export dropdown options with counts and the replay CSV without predictions."""
    print("7/7 Exporting options.json and replay/test_incidents.csv...")

    # Dropdown options from train_val (levels seen >= 30 times)
    options = {}
    for feat in config.FEATURES:
        if feat in ["hour", "weekday"]:
            # Server-derived features, export all possible values
            s = train_val[feat].value_counts()
            options[feat] = [
                {"value": str(val), "count": int(cnt), "is_frequent": True}
                for val, cnt in s.items()
            ]
            continue

        counts = train_val[feat].value_counts(dropna=True)
        feat_options = []
        for val, cnt in counts.items():
            feat_options.append({
                "value": str(val),
                "count": int(cnt),
                "is_frequent": bool(cnt >= config.MIN_FREQUENCY),
            })
        # Count missing values in train_val
        n_missing = int(train_val[feat].isna().sum())
        feat_options.append({
            "value": "Unknown / not provided",
            "is_missing_marker": True,
            "count": n_missing,
            "is_frequent": True,
        })
        options[feat] = feat_options

    with open(ARTIFACTS_DIR / "options.json", "w", encoding="utf-8") as f:
        json.dump(options, f, indent=2)

    # Replay CSV: sorted by opened_at, raw features only, resolution_hours, NO predictions
    replay_cols = [
        config.ID_COL,
        "opened_at",
        "priority",
        "impact",
        "urgency",
        "category",
        "subcategory",
        "u_symptom",
        "assignment_group",
        "location",
        "contact_type",
        "opened_by",
        "sys_created_by",
        config.TARGET,
    ]
    test_sorted = test[replay_cols].sort_values("opened_at").copy()
    test_sorted.to_csv(REPLAY_DIR / "test_incidents.csv", index=False)

    # Model comparison, tuning results, sensitivity checks from reports/tables
    def convert_csv_to_json(csv_path, json_path):
        if csv_path.exists():
            df = pd.read_csv(csv_path)
            # Replace NaNs with null
            records = df.where(pd.notna(df), None).to_dict(orient="records")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(records, f, indent=2)

    tables_dir = config.TABLES_DIR
    convert_csv_to_json(tables_dir / "model_comparison_validation.csv", METRICS_DIR / "model_comparison_validation.json")
    convert_csv_to_json(tables_dir / "model_comparison_tuned.csv", METRICS_DIR / "model_comparison_tuned.json")
    convert_csv_to_json(tables_dir / "tuning_results.csv", METRICS_DIR / "tuning_results.json")
    convert_csv_to_json(tables_dir / "sensitivity_checks.csv", METRICS_DIR / "sensitivity_checks.json")

    # Combine validation and tuned model comparison into model_comparison.json
    val_comp = pd.read_csv(tables_dir / "model_comparison_validation.csv").where(pd.notna, None).to_dict(orient="records")
    tuned_comp = pd.read_csv(tables_dir / "model_comparison_tuned.csv").where(pd.notna, None).to_dict(orient="records")
    with open(METRICS_DIR / "model_comparison.json", "w", encoding="utf-8") as f:
        json.dump({"default_models_validation": val_comp, "tuned_models_validation": tuned_comp}, f, indent=2)


def main():
    """Main export routine."""
    print("=== Starting artifact export ===")
    validate_export_inputs()
    ensure_directories()
    export_raw_and_summary()

    table = features.load_table()
    export_eda_and_splits(table)

    pipeline, train_val, test, y_test, pred, base_pred = train_and_export_model(table)
    export_test_evaluations(pipeline, train_val, test, y_test, pred, base_pred)
    export_prediction_ranges(test, y_test, pred)
    export_options_and_replay(table, train_val, test)

    print("=== All artifacts exported and verified successfully! ===")


if __name__ == "__main__":
    main()
