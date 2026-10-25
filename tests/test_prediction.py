"""Tests for prediction endpoints: nominal, missing values, warnings, anti-leakage, and batch limits."""
import os
os.environ["LOKY_MAX_CPU_COUNT"] = "4"

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

SAMPLE_INCIDENT = {
    "opened_at": "2016-05-12T14:30:00",
    "priority": "3 - Moderate",
    "impact": "2 - Medium",
    "urgency": "2 - Medium",
    "category": "Category 26",
    "subcategory": "Subcategory 174",
    "u_symptom": "Symptom 491",
    "assignment_group": "Group 70",
    "location": "Location 204",
    "contact_type": "Phone",
    "opened_by": "Opened by  17",
    "sys_created_by": "Created by 10",
}


def test_predict_nominal():
    """Nominal prediction returns positive duration, 80% range, probability, and disclaimer."""
    r = client.post("/api/v1/predict", json=SAMPLE_INCIDENT)
    assert r.status_code == 200
    res = r.json()

    assert res["predicted_hours"] >= 0.0
    assert "about" in res["predicted_human"].lower()
    assert "range_80" in res
    assert res["range_80"]["q10_hours"] <= res["range_80"]["q90_hours"]
    assert 0.0 <= res["prob_over_24h"] <= 100.0
    assert "disclaimer" in res
    assert "guarantee" in res["disclaimer"].lower()


def test_predict_with_null_and_missing_fields():
    """All categorical fields are optional and null is accepted as a valid missing level."""
    payload = {
        "opened_at": "2016-05-12T14:30:00",
        "priority": None,
        "impact": None,
        "urgency": None,
        "category": None,
        "subcategory": None,
        "u_symptom": None,
        "assignment_group": None,
        "location": None,
        "contact_type": None,
        "opened_by": None,
        "sys_created_by": None,
    }
    r = client.post("/api/v1/predict", json=payload)
    assert r.status_code == 200
    res = r.json()
    assert res["predicted_hours"] >= 0.0
    # Should include warning for multiple missing fields
    assert any("missing" in w.lower() for w in res["warnings"])


def test_predict_with_unseen_category_generates_warning():
    """Values never seen during training are accepted via infrequent fallback and trigger a warning."""
    payload = {
        **SAMPLE_INCIDENT,
        "assignment_group": "Group_Never_Seen_Before_9999",
        "category": "Category_Completely_New",
    }
    r = client.post("/api/v1/predict", json=payload)
    assert r.status_code == 200
    res = r.json()
    assert res["predicted_hours"] >= 0.0

    warnings = res["warnings"]
    assert len(warnings) >= 2
    assert any("Group_Never_Seen_Before_9999" in w for w in warnings)
    assert any("Category_Completely_New" in w for w in warnings)


def test_predict_rejects_post_opening_leakage_fields():
    """Forbidden fields from later in incident lifecycle MUST be rejected with HTTP 422."""
    forbidden_fields = [
        "resolved_at",
        "closed_at",
        "reassignment_count",
        "reopen_count",
        "sys_mod_count",
        "incident_state",
        "active",
        "made_sla",
        "assigned_to",
        "resolved_by",
        "closed_code",
    ]

    for field in forbidden_fields:
        leakage_payload = {
            **SAMPLE_INCIDENT,
            field: "leakage_value_123",
        }
        r = client.post("/api/v1/predict", json=leakage_payload)
        assert r.status_code == 422, f"Failed to reject forbidden leakage field '{field}'"
        detail_str = str(r.json()).lower()
        assert "forbidden" in detail_str or "leakage" in detail_str or "extra" in detail_str, (
            f"Error message for '{field}' did not clearly explain leakage prevention: {r.json()}"
        )


def test_predict_rejects_invalid_date():
    """Non-ISO or malformed datetime strings must return HTTP 422."""
    bad_payload = {
        **SAMPLE_INCIDENT,
        "opened_at": "invalid-date-not-an-iso-string",
    }
    r = client.post("/api/v1/predict", json=bad_payload)
    assert r.status_code == 422


def test_batch_prediction_nominal():
    """Batch prediction successfully scores up to 500 incidents."""
    batch_payload = {
        "incidents": [SAMPLE_INCIDENT for _ in range(5)]
    }
    r = client.post("/api/v1/predict/batch", json=batch_payload)
    assert r.status_code == 200
    res = r.json()
    assert res["count"] == 5
    assert len(res["predictions"]) == 5


def test_batch_prediction_exceeding_limit_rejected():
    """Batch prediction requests with >500 tickets must be rejected."""
    oversized_payload = {
        "incidents": [SAMPLE_INCIDENT for _ in range(501)]
    }
    r = client.post("/api/v1/predict/batch", json=oversized_payload)
    assert r.status_code == 422
