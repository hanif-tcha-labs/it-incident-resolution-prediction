"""Pydantic schemas for requests and responses."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class IncidentInput(BaseModel):
    """Input ticket at opening time.

    Only fields available when the incident is opened are permitted.
    Fields from later in the incident lifecycle (e.g., resolved_at,
    closed_at, reassignment_count) are strictly forbidden to prevent leakage.
    """
    opened_at: datetime = Field(
        ...,
        description="ISO 8601 opening date and time (e.g. 2016-04-15T10:30:00)."
    )
    priority: Optional[str] = Field(None, description="Priority level (e.g. '3 - Moderate').")
    impact: Optional[str] = Field(None, description="Impact level (e.g. '2 - Medium').")
    urgency: Optional[str] = Field(None, description="Urgency level (e.g. '2 - Medium').")
    category: Optional[str] = Field(None, description="Incident category (e.g. 'Category 26').")
    subcategory: Optional[str] = Field(None, description="Incident subcategory.")
    u_symptom: Optional[str] = Field(None, description="Reported symptom code.")
    assignment_group: Optional[str] = Field(None, description="Initial assignment group.")
    location: Optional[str] = Field(None, description="Caller location code.")
    contact_type: Optional[str] = Field(None, description="Contact channel (e.g. 'Phone').")
    opened_by: Optional[str] = Field(None, description="Agent who opened the ticket.")
    sys_created_by: Optional[str] = Field(None, description="User who created the record in the system.")

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "opened_at": "2016-04-15T14:30:00",
                "priority": "3 - Moderate",
                "impact": "2 - Medium",
                "urgency": "2 - Medium",
                "category": "Category 26",
                "subcategory": "Subcategory 174",
                "u_symptom": "Symptom 491",
                "assignment_group": "Group 70",
                "location": "Location 204",
                "contact_type": "Phone",
                "opened_by": "Opened by 17",
                "sys_created_by": "Created by 10",
            }
        }
    )


class PredictionRange(BaseModel):
    """Empirical 80% range computed from test set incidents with similar predictions."""
    bin: str
    q10_hours: float
    q50_hours: float
    q90_hours: float
    n_test_samples: int
    pct_over_24h: float
    text: str


class PredictionResponse(BaseModel):
    """Prediction outcome, empirical bounds, warnings, and limitations."""
    predicted_hours: float
    predicted_human: str
    range_80: PredictionRange
    prob_over_24h: float
    warnings: List[str]
    model_version: str
    request_id: str
    disclaimer: str


class BatchPredictionRequest(BaseModel):
    """Batch prediction request for multiple incidents (max 500)."""
    incidents: List[IncidentInput] = Field(..., max_length=500)


class BatchPredictionResponse(BaseModel):
    """Batch prediction results."""
    predictions: List[PredictionResponse]
    count: int


class ErrorResponse(BaseModel):
    """Standardized API error response."""
    error: str
    detail: Any
    request_id: Optional[str] = None
