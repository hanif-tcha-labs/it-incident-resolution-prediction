"""Prediction and options endpoints."""
from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException

from app import schemas
from app.services import artifacts
from app.services.model import ModelService

router = APIRouter(prefix="/api/v1", tags=["Prediction"])


@router.get("/options")
def get_form_options() -> Dict[str, List[Dict[str, Any]]]:
    """Available dropdown options for categorical features with historical frequencies."""
    return artifacts.load_json_artifact("options.json")


@router.post("/predict", response_model=schemas.PredictionResponse)
def predict_incident(incident: schemas.IncidentInput) -> schemas.PredictionResponse:
    """Predict resolution time for an incident ticket at opening."""
    service = ModelService.get_instance()
    try:
        return service.predict(incident)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference failed: {str(e)}") from e


@router.post("/predict/batch", response_model=schemas.BatchPredictionResponse)
def predict_batch(request: schemas.BatchPredictionRequest) -> schemas.BatchPredictionResponse:
    """Batch prediction endpoint for up to 500 incidents."""
    service = ModelService.get_instance()
    try:
        results = service.predict_batch(request.incidents)
        return schemas.BatchPredictionResponse(predictions=results, count=len(results))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch inference failed: {str(e)}") from e
