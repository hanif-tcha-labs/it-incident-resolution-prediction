"""Tests for all GET API endpoints and HTML pages."""
import os
os.environ["LOKY_MAX_CPU_COUNT"] = "4"

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_endpoint():
    """Health endpoint must return 200, status ok, and confirm model and artifacts present."""
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["model_loaded"] is True
    assert data["artifacts_present"] is True
    assert len(data["missing_artifacts"]) == 0


def test_project_endpoints():
    """Project overview, data dictionary, and data quality endpoints."""
    r_model = client.get("/api/v1/model")
    assert r_model.status_code == 200
    assert "hyperparameters" in r_model.json()

    r_overview = client.get("/api/v1/project/overview")
    assert r_overview.status_code == 200
    assert r_overview.json()["key_figures"]["total_events"] == 141712

    r_dict = client.get("/api/v1/data/dictionary")
    assert r_dict.status_code == 200
    assert len(r_dict.json()) == 36

    r_qual = client.get("/api/v1/data/quality")
    assert r_qual.status_code == 200
    assert r_qual.json()["summary"]["n_with_target"] == 24905


def test_eda_endpoints():
    """Target distribution and group duration breakdown endpoints."""
    r_dist = client.get("/api/v1/eda/target-distribution")
    assert r_dist.status_code == 200
    assert r_dist.json()["count"] == 24905

    for grp in ["priority", "impact", "category", "weekday"]:
        r_grp = client.get(f"/api/v1/eda/by-group?by={grp}")
        assert r_grp.status_code == 200
        assert len(r_grp.json()["categories"]) > 0

    # Invalid group should return 400
    r_bad = client.get("/api/v1/eda/by-group?by=invalid_group_xyz")
    assert r_bad.status_code == 400


def test_models_and_evaluation_endpoints():
    """Features, validation strategy, model comparison, evaluation, and importance."""
    r_feat = client.get("/api/v1/features")
    assert r_feat.status_code == 200
    assert len(r_feat.json()["features"]) == 13

    r_strat = client.get("/api/v1/validation/strategy")
    assert r_strat.status_code == 200
    assert len(r_strat.json()["weekly_target_evolution"]) > 0

    r_comp = client.get("/api/v1/models/comparison")
    assert r_comp.status_code == 200
    assert len(r_comp.json()["default_models_validation"]) > 0

    r_final = client.get("/api/v1/models/final")
    assert r_final.status_code == 200

    r_err_dur = client.get("/api/v1/evaluation/errors-by-group?by=duration")
    assert r_err_dur.status_code == 200

    r_weekly = client.get("/api/v1/evaluation/weekly")
    assert r_weekly.status_code == 200

    r_imp = client.get("/api/v1/interpretation/importance")
    assert r_imp.status_code == 200
    assert len(r_imp.json()["individual"]) == 13


def test_options_and_simulation_endpoints():
    """Options and simulation replay endpoints."""
    r_opt = client.get("/api/v1/options")
    assert r_opt.status_code == 200
    assert "assignment_group" in r_opt.json()

    r_sim = client.get("/api/v1/simulation/incidents?offset=0&limit=10")
    assert r_sim.status_code == 200
    data = r_sim.json()
    assert data["total"] == 4981
    assert len(data["incidents"]) == 10


def test_all_html_pages_render():
    """All 12 dashboard views must return 200 OK and valid HTML."""
    pages = [
        "/overview", "/quality", "/eda", "/features", "/validation",
        "/models", "/results", "/interpretation",
        "/predict", "/replay", "/monitoring", "/limits"
    ]
    for page in pages:
        r = client.get(page)
        assert r.status_code == 200, f"Page {page} returned status {r.status_code}"
        assert "<html" in r.text.lower(), f"Page {page} does not contain valid HTML"


def test_live_simulator_is_first_navigation_item():
    response = client.get("/overview")
    assert response.status_code == 200
    html = response.text

    nav_start = html.index('<nav class="sidebar-nav">')
    first_link_start = html.index('<a href="/replay"', nav_start)
    next_link_start = html.index('<a href="/predict"', first_link_start)
    assert "Live Simulator" in html[first_link_start:next_link_start]
    assert "<h1>HTVEX AI</h1>" in html
    assert "HTVEX AI &bull; Incident Forecasting" in html
    assert "ResolveML" not in html
    assert "<footer" not in html
    docs_link = html.index('<a href="/docs"')
    limits_link = html.index('<a href="/limits"')
    sidebar_footer = html.index('<div class="sidebar-footer">')
    assert docs_link < limits_link < sidebar_footer
    assert client.get("/limits").status_code == 200
