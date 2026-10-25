"""Project overview, data dictionary, and data quality endpoints."""
from typing import Any, Dict, List
from fastapi import APIRouter

from app.services import artifacts

router = APIRouter(prefix="/api/v1", tags=["Project & Data"])


@router.get("/model")
def get_model_card() -> Dict[str, Any]:
    """Get model card with metadata, training versions, parameters, and baseline metrics."""
    return artifacts.load_json_artifact("model/model_card.json")


@router.get("/project/overview")
def get_project_overview() -> Dict[str, Any]:
    """Business problem, target definition, lifecycle, and key headline figures."""
    summary = artifacts.load_json_artifact("metrics/data_summary.json")
    split = artifacts.load_json_artifact("metrics/split.json")
    test_metrics = artifacts.load_json_artifact("metrics/final_test_metrics.json")

    return {
        "project_title": "IT Incident Resolution Time Prediction",
        "business_problem": (
            "Predict the total resolution time of IT incidents at the exact moment of ticket creation "
            "using only initial information, to assist support teams in triaging and SLA risk assessment."
        ),
        "target": {
            "name": "resolution_hours",
            "unit": "hours",
            "definition": "Timestamp of the last resolution minus opening timestamp (opened_at).",
            "prediction_moment": "Incident opening (first event logged).",
        },
        "process_pipeline": [
            "Event log (141,712 events across 24,918 incidents)",
            "Incident table reconstruction (24,905 incidents with valid resolution)",
            "Feature extraction (first event values only, strict leakage boundary)",
            "Temporal train / validation / test split (60% / 20% / 20%)",
            "Model training (HistGradientBoosting on log-transformed target)",
            "Evaluation on unseen test set with bootstrap intervals",
        ],
        "key_figures": {
            "total_events": summary.get("n_events"),
            "total_incidents": summary.get("n_incidents"),
            "incidents_with_target": summary.get("n_with_target"),
            "test_mae_model_hours": test_metrics.get("model", {}).get("MAE"),
            "test_mae_baseline_hours": test_metrics.get("baseline", {}).get("MAE"),
            "test_mae_reduction_pct": 11.5,
        },
    }


@router.get("/data/dictionary")
def get_data_dictionary() -> List[Dict[str, Any]]:
    """Data dictionary describing all 36 original columns, meanings, and availability."""
    return artifacts.load_json_artifact("metrics/data_dictionary.json")


@router.get("/data/quality")
def get_data_quality() -> Dict[str, Any]:
    """Data quality audit: missing values, duplicate checks, special cases (unresolved, reopened)."""
    summary = artifacts.load_json_artifact("metrics/data_summary.json")

    return {
        "summary": {
            "n_events": summary.get("n_events"),
            "n_incidents": summary.get("n_incidents"),
            "n_with_target": summary.get("n_with_target"),
            "n_without_target": summary.get("n_without_target"),
            "n_created_resolved": summary.get("n_created_resolved"),
            "pct_created_resolved": summary.get("pct_created_resolved"),
            "n_reopened": summary.get("n_reopened"),
            "pct_reopened": summary.get("pct_reopened"),
            "exact_duplicates": summary.get("exact_duplicates"),
        },
        "unresolved_incidents_detail": {
            "count": 13,
            "reason": "Ticket never reached state 'Resolved' and had no resolved_at timestamp. Excluded from target.",
        },
        "created_already_resolved_detail": {
            "count": 1819,
            "percentage": 7.3,
            "reason": "Incidents logged after resolution had already occurred. Kept in main model; sensitivity check showed negligible impact.",
        },
        "reopened_incidents_detail": {
            "count": 275,
            "percentage": 1.1,
            "reason": "Incidents reopened after initial resolution. Target uses the final resolution timestamp.",
        },
        "missing_values": summary.get("missing_by_column", {}),
    }
