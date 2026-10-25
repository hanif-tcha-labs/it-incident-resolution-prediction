"""Features, validation strategy, and model comparison endpoints."""
from typing import Any, Dict
from fastapi import APIRouter

from app.services import artifacts

router = APIRouter(prefix="/api/v1", tags=["Models & Validation"])


@router.get("/features")
def get_features_info() -> Dict[str, Any]:
    """Retained features, excluded variables with explicit justification, and leakage prevention."""
    return artifacts.load_json_artifact("metrics/features.json")


@router.get("/validation/strategy")
def get_validation_strategy() -> Dict[str, Any]:
    """Temporal split definitions, date bounds, median duration shifts, and weekly regime change."""
    split_info = artifacts.load_json_artifact("metrics/split.json")
    weekly_target = artifacts.load_json_artifact("metrics/weekly_target.json")

    return {
        "split_strategy": "Chronological split: oldest 60% train, next 20% validation, last 20% test",
        "rationale": "Preserves chronological evaluation on incidents that occur after the training period.",
        "splits": split_info,
        "weekly_target_evolution": weekly_target,
        "regime_shift_warning": (
            "Noticeable operational regime shift starting March 28, 2016: median resolution time dropped from ~80h "
            "down to ~2h. Preserving temporal order is essential to test model robustness across regime changes."
        ),
    }


@router.get("/models/comparison")
def get_models_comparison() -> Dict[str, Any]:
    """Model comparison tables: baseline, Ridge, Random Forest, HistGradientBoosting (defaults and tuned)."""
    comparison = artifacts.load_json_artifact("metrics/model_comparison.json")
    tuning = artifacts.load_json_artifact("metrics/tuning_results.json")
    sensitivity = artifacts.load_json_artifact("metrics/sensitivity_checks.json")

    return {
        "default_models_validation": comparison.get("default_models_validation", []),
        "tuned_models_validation": comparison.get("tuned_models_validation", []),
        "tuning_configurations_tested": tuning,
        "sensitivity_checks": sensitivity,
        "key_takeaways": [
            "Log1p transformation of the target is the single most critical factor (reduces validation MAE from ~153h to ~106h).",
            "HistGradientBoosting achieved lowest validation MAE (106.22h) and trains in ~19s vs 37s for Random Forest.",
            "Sensitivity analysis confirmed results are robust to removing sys_created_by or excluding created-resolved incidents.",
        ],
    }


@router.get("/models/final")
def get_final_model_details() -> Dict[str, Any]:
    """Final model specification, hyperparameters, test set performance, and bootstrap interval."""
    card = artifacts.load_json_artifact("model/model_card.json")
    metrics_data = artifacts.load_json_artifact("metrics/final_test_metrics.json")

    return {
        "model_card": card,
        "test_metrics": metrics_data,
        "bootstrap_summary": (
            f"95% bootstrap confidence interval on model test MAE is [{metrics_data['bootstrap']['mae_model_ci'][0]}, "
            f"{metrics_data['bootstrap']['mae_model_ci'][1]}] hours. "
            f"Expected MAE reduction vs baseline is [{metrics_data['bootstrap']['mae_reduction_ci'][0]}, "
            f"{metrics_data['bootstrap']['mae_reduction_ci'][1]}] hours."
        ),
    }
