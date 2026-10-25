"""Simulation and stream replay endpoints."""
from typing import Any, Dict, List
from fastapi import APIRouter, Query
import pandas as pd

from app import config

router = APIRouter(prefix="/api/v1/simulation", tags=["Simulation & Replay"])

_TEST_INCIDENTS_DF: pd.DataFrame = None


def get_test_incidents() -> pd.DataFrame:
    """Load and cache test incidents for streaming replay."""
    global _TEST_INCIDENTS_DF
    if _TEST_INCIDENTS_DF is None:
        if not config.REPLAY_CSV_PATH.exists():
            raise FileNotFoundError(
                f"Replay dataset not found at {config.REPLAY_CSV_PATH}. "
                "Run 'python -m src.export_artifacts' first."
            )
        _TEST_INCIDENTS_DF = pd.read_csv(config.REPLAY_CSV_PATH)
    return _TEST_INCIDENTS_DF


@router.get("/incidents")
def get_simulation_incidents(
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(100, ge=1, le=1000, description="Number of incidents to return"),
) -> Dict[str, Any]:
    """Retrieve chronologically ordered test set incidents for live replay simulation.

    Does NOT contain model predictions (predictions must be requested from the API during simulation).
    """
    df = get_test_incidents()
    total = len(df)
    subset = df.iloc[offset : offset + limit]

    # Convert NaN to None for clean JSON serialization
    records = subset.where(pd.notna(subset), None).to_dict(orient="records")

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "incidents": records,
    }
