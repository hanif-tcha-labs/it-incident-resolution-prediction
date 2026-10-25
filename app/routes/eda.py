"""Exploratory data analysis endpoints."""
from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException, Query

from app.services import artifacts

router = APIRouter(prefix="/api/v1/eda", tags=["EDA"])


@router.get("/target-distribution")
def get_target_distribution() -> Dict[str, Any]:
    """Target duration distribution, percentiles, log-scale histogram, and duration shares."""
    return artifacts.load_json_artifact("eda/target_distribution.json")


@router.get("/by-group")
def get_eda_by_group(
    by: str = Query(
        "priority",
        description="Grouping variable: priority, impact, urgency, category, assignment_group, contact_type, weekday, hour, month"
    )
) -> Dict[str, Any]:
    """Duration statistics (sample size, median, mean, p90) grouped by category."""
    all_groups = artifacts.load_json_artifact("eda/by_group.json")

    if by not in all_groups:
        valid_keys = list(all_groups.keys())
        raise HTTPException(
            status_code=400,
            detail=f"Invalid grouping variable '{by}'. Choose from: {valid_keys}"
        )

    return {
        "group_by": by,
        "categories": all_groups[by],
    }
