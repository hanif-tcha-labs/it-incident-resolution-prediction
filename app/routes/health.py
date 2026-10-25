"""Health and system status check endpoint."""
import sys
from typing import Any, Dict
from fastapi import APIRouter
import pandas as pd
import sklearn

from app import config
from app.services import artifacts
from app.services.model import ModelService

router = APIRouter(tags=["Health"])


@router.get("/health")
def health_check() -> Dict[str, Any]:
    """Health check: verifies model loaded, required artifacts, and library versions."""
    model_service = ModelService.get_instance()
    try:
        model_service.ensure_loaded()
    except Exception:
        pass
    model_loaded = model_service.pipeline is not None

    required_artifacts = [
        "model/final_pipeline.joblib",
        "model/model_card.json",
        "metrics/data_summary.json",
        "metrics/data_dictionary.json",
        "metrics/features.json",
        "metrics/split.json",
        "metrics/weekly_target.json",
        "metrics/final_test_metrics.json",
        "metrics/errors_by_group.json",
        "metrics/permutation_importance.json",
        "metrics/weekly_errors_test.json",
        "metrics/prediction_ranges.json",
        "eda/target_distribution.json",
        "eda/by_group.json",
        "options.json",
        "replay/test_incidents.csv",
    ]

    missing_artifacts = [
        art for art in required_artifacts
        if not (config.ARTIFACTS_DIR / art).exists()
    ]

    warnings = []
    card = model_service.model_card
    trained_versions = card.get("versions", {})
    current_sklearn = sklearn.__version__
    current_pandas = pd.__version__

    if trained_versions:
        expected_sklearn = trained_versions.get("scikit_learn")
        expected_pandas = trained_versions.get("pandas")
        if expected_sklearn and expected_sklearn != current_sklearn:
            warnings.append(
                f"Scikit-learn version mismatch: trained on {expected_sklearn}, running {current_sklearn}"
            )
        if expected_pandas and expected_pandas != current_pandas:
            warnings.append(
                f"Pandas version mismatch: trained on {expected_pandas}, running {current_pandas}"
            )

    status = "ok" if (model_loaded and not missing_artifacts) else "degraded"

    return {
        "status": status,
        "model_loaded": model_loaded,
        "model_version": model_service.version,
        "artifacts_present": len(missing_artifacts) == 0,
        "missing_artifacts": missing_artifacts,
        "environment": {
            "python": sys.version.split()[0],
            "scikit_learn": current_sklearn,
            "pandas": current_pandas,
        },
        "warnings": warnings,
    }
