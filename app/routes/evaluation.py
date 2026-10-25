"""Evaluation, error breakdowns, and model explainability endpoints."""
from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException, Query

from app.services import artifacts

router = APIRouter(prefix="/api/v1", tags=["Evaluation & Interpretation"])


@router.get("/evaluation/errors-by-group")
def get_errors_by_group(
    by: str = Query(
        "duration",
        description="Grouping variable: duration, priority, category"
    )
) -> Dict[str, Any]:
    """Error metrics (MAE baseline, MAE model, signed error, share of total error) by group."""
    errors_data = artifacts.load_json_artifact("metrics/errors_by_group.json")

    group_key = f"by_{by}"
    if group_key not in errors_data:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid grouping variable '{by}'. Choose from: 'duration', 'priority', 'category'"
        )

    return {
        "grouped_by": by,
        "records": errors_data[group_key],
        "key_insight": (
            "Incidents lasting over 24h represent only 36% of test incidents but account for ~91% of total model error. "
            "The model excels on fast tickets (<1h) but systematically underestimates slow incidents."
            if by == "duration" else ""
        ),
    }


@router.get("/evaluation/weekly")
def get_weekly_test_errors() -> List[Dict[str, Any]]:
    """Weekly test set error progression (model MAE vs baseline MAE over time)."""
    return artifacts.load_json_artifact("metrics/weekly_errors_test.json")


@router.get("/interpretation/importance")
def get_feature_importance() -> Dict[str, Any]:
    """Permutation importance on test set (individual features and grouped subsets)."""
    return artifacts.load_json_artifact("metrics/permutation_importance.json")
