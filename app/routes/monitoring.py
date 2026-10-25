"""Model monitoring and prediction logging endpoints."""
from typing import Any, Dict, List
from fastapi import APIRouter, Query

from app.services import prediction_log

router = APIRouter(prefix="/api/v1/monitoring", tags=["Monitoring"])


@router.get("/summary")
def get_monitoring_summary() -> Dict[str, Any]:
    """Monitoring statistics: prediction volume, warnings rate, duration distribution, drift signals."""
    return prediction_log.get_prediction_summary()


@router.get("/predictions")
def get_recent_predictions(
    limit: int = Query(50, ge=1, le=500, description="Max number of recent predictions to return")
) -> List[Dict[str, Any]]:
    """Retrieve recent prediction audit log entries from SQLite."""
    return prediction_log.get_recent_predictions(limit=limit)
