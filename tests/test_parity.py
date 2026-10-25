"""Tests validating numerical parity between API prediction and direct pipeline call."""
import os
os.environ["LOKY_MAX_CPU_COUNT"] = "4"

from datetime import datetime
import joblib
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app import config
from app.main import app

client = TestClient(app)


def test_prediction_parity_with_direct_pipeline():
    """Verify that API prediction returns the exact same number as pipeline.predict()."""
    # Load raw pipeline directly
    pipeline = joblib.load(config.MODEL_PATH)

    sample = {
        "opened_at": "2016-05-15T09:45:00",
        "priority": "2 - High",
        "impact": "1 - High",
        "urgency": "2 - Medium",
        "category": "Category 42",
        "subcategory": "Subcategory 223",
        "u_symptom": "Symptom 491",
        "assignment_group": "Group 25",
        "location": "Location 143",
        "contact_type": "Phone",
        "opened_by": "Opened by  17",
        "sys_created_by": "Created by 10",
    }

    # API prediction
    r = client.post("/api/v1/predict", json=sample)
    assert r.status_code == 200
    api_predicted_hours = r.json()["predicted_hours"]

    # Direct scikit-learn pipeline prediction
    opened_dt = datetime.fromisoformat(sample["opened_at"])
    direct_row = {
        "priority": sample["priority"],
        "impact": sample["impact"],
        "urgency": sample["urgency"],
        "category": sample["category"],
        "subcategory": sample["subcategory"],
        "u_symptom": sample["u_symptom"],
        "assignment_group": sample["assignment_group"],
        "location": sample["location"],
        "contact_type": sample["contact_type"],
        "opened_by": sample["opened_by"],
        "sys_created_by": sample["sys_created_by"],
        "hour": str(opened_dt.hour),
        "weekday": str(opened_dt.weekday()),
    }
    feature_order = [
        "priority", "impact", "urgency", "category", "subcategory", "u_symptom",
        "assignment_group", "location", "contact_type", "opened_by", "sys_created_by",
        "hour", "weekday"
    ]
    df_direct = pd.DataFrame([direct_row])[feature_order]
    direct_raw = pipeline.predict(df_direct)
    direct_clipped = float(np.clip(direct_raw[0], 0, None))
    direct_rounded = round(direct_clipped, 2)

    assert abs(api_predicted_hours - direct_rounded) < 1e-5, (
        f"API prediction ({api_predicted_hours}) != direct pipeline prediction ({direct_rounded})"
    )
