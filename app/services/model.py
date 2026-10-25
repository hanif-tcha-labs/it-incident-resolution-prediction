"""Model loading and prediction service."""
import os
import uuid
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd

from app import config, schemas
from app.services import artifacts, prediction_log

# Avoid CPU count lookup warning on Windows
os.environ["LOKY_MAX_CPU_COUNT"] = "4"

DISCLAIMER_TEXT = (
    "Model prediction is a statistical estimate based on historical patterns, not an operational guarantee. "
    "Correlation does not imply causality (adjusting fields does not guarantee different resolution times). "
    "Accuracy is significantly lower for complex incidents taking more than 24 hours."
)


def format_human_duration(hours: float) -> str:
    """Format duration in hours into a readable text string."""
    if hours < 1.0:
        mins = int(round(hours * 60))
        return f"about {max(mins, 1)} minute{'s' if mins > 1 else ''}"
    if hours < 24.0:
        h = int(hours)
        m = int(round((hours - h) * 60))
        if m == 0:
            return f"about {h} hour{'s' if h > 1 else ''}"
        return f"about {h} h {m:02d} min"
    days = hours / 24.0
    h = int(hours % 24)
    if days < 7.0:
        return f"about {int(days)} day{'s' if int(days) > 1 else ''} {h} h ({hours:.1f} hours)"
    return f"about {days:.1f} days ({hours:.1f} hours)"


class ModelService:
    """Singleton service wrapping the trained scikit-learn pipeline."""

    _instance: Optional["ModelService"] = None

    def __init__(self):
        self.pipeline = None
        self.model_card: Dict[str, Any] = {}
        self.prediction_ranges: List[Dict[str, Any]] = []
        self.options: Dict[str, List[Dict[str, Any]]] = {}
        self.frequent_levels: Dict[str, set] = {}
        self.all_known_levels: Dict[str, set] = {}
        self.version = "1.0.0"

    @classmethod
    def get_instance(cls) -> "ModelService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def ensure_loaded(self):
        """Ensure pipeline and artifacts are loaded."""
        if self.pipeline is None:
            self.load()

    def load(self):
        """Load the pipeline and metadata artifacts."""
        if not config.MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Model pipeline not found at {config.MODEL_PATH}. "
                "Run 'python -m src.export_artifacts' first."
            )
        self.pipeline = joblib.load(config.MODEL_PATH)
        self.model_card = artifacts.load_json_artifact("model/model_card.json")
        self.prediction_ranges = artifacts.load_json_artifact("metrics/prediction_ranges.json")
        self.options = artifacts.load_json_artifact("options.json")

        # Precompute set of seen values per feature for fast OOD checks
        for feat, opt_list in self.options.items():
            freq_set = set()
            all_set = set()
            for opt in opt_list:
                if not opt.get("is_missing_marker"):
                    val = str(opt["value"])
                    all_set.add(val)
                    if opt.get("is_frequent", True):
                        freq_set.add(val)
            self.frequent_levels[feat] = freq_set
            self.all_known_levels[feat] = all_set

        self.version = self.model_card.get("versions", {}).get("scikit_learn", "1.7.2")
        prediction_log.init_db()

    def get_prediction_range(self, predicted_hours: float) -> Tuple[Dict[str, Any], float]:
        """Find the matching empirical range and probability of exceeding 24 hours."""
        for r in self.prediction_ranges:
            b_min = r["min_pred_hours"]
            b_max = r["max_pred_hours"]
            if b_max is not None:
                if b_min <= predicted_hours < b_max:
                    return r, r["pct_over_24h"]
            else:
                if predicted_hours >= b_min:
                    return r, r["pct_over_24h"]

        # Fallback to last range
        fallback = self.prediction_ranges[-1] if self.prediction_ranges else {}
        return fallback, fallback.get("pct_over_24h", 50.0)

    def predict(self, incident: schemas.IncidentInput) -> schemas.PredictionResponse:
        """Run inference on an incident ticket."""
        self.ensure_loaded()
        if self.pipeline is None:
            raise RuntimeError("Model pipeline is not loaded.")

        request_id = str(uuid.uuid4())
        warnings: List[str] = []

        # Derive hour and weekday from opened_at
        hour = str(incident.opened_at.hour)
        weekday = str(incident.opened_at.weekday())

        # Collect 13 features in exact pipeline order
        feature_order = [
            "priority", "impact", "urgency", "category", "subcategory", "u_symptom",
            "assignment_group", "location", "contact_type", "opened_by", "sys_created_by",
            "hour", "weekday"
        ]

        row_dict = {
            "hour": hour,
            "weekday": weekday,
        }

        # Check for unseen or infrequent categories
        missing_count = 0
        input_data = incident.model_dump()
        for feat in feature_order:
            if feat in ["hour", "weekday"]:
                continue
            val = input_data.get(feat)
            if val is None or str(val).strip() == "" or str(val).lower() == "none":
                row_dict[feat] = None
                missing_count += 1
            else:
                val_str = str(val).strip()
                row_dict[feat] = val_str
                # Check known levels
                known = self.all_known_levels.get(feat, set())
                if val_str not in known:
                    warnings.append(
                        f"Field '{feat}' value '{val_str}' was never seen during training (grouped as rare level)."
                    )

        if missing_count >= 5:
            warnings.append(
                f"Multiple input fields ({missing_count}/11) are missing. Prediction relies heavily on baseline defaults."
            )

        # Build DataFrame with exact feature order
        df_input = pd.DataFrame([row_dict])[feature_order]

        # Inherent pipeline inference
        raw_pred = self.pipeline.predict(df_input)
        pred_clipped = float(np.clip(raw_pred[0], 0, None))
        pred_rounded = round(pred_clipped, 2)

        # Range and uncertainty
        range_data, prob_24h = self.get_prediction_range(pred_rounded)
        range_obj = schemas.PredictionRange(
            bin=range_data.get("bin", "unknown"),
            q10_hours=range_data.get("q10_hours", 0.0),
            q50_hours=range_data.get("q50_hours", 0.0),
            q90_hours=range_data.get("q90_hours", 0.0),
            n_test_samples=range_data.get("n_test_samples", 0),
            pct_over_24h=range_data.get("pct_over_24h", 0.0),
            text=range_data.get("interpretation", ""),
        )

        human_str = format_human_duration(pred_rounded)

        response = schemas.PredictionResponse(
            predicted_hours=pred_rounded,
            predicted_human=human_str,
            range_80=range_obj,
            prob_over_24h=round(prob_24h, 1),
            warnings=warnings,
            model_version=f"hgb-{self.version}",
            request_id=request_id,
            disclaimer=DISCLAIMER_TEXT,
        )

        # Persist to SQLite
        try:
            prediction_log.log_prediction(
                request_id=request_id,
                opened_at=incident.opened_at.isoformat(),
                inputs=incident.model_dump(mode="json"),
                predicted_hours=pred_rounded,
                output=response.model_dump(mode="json"),
                model_version=f"hgb-{self.version}",
                has_warnings=bool(warnings),
            )
        except Exception as e:
            print(f"Warning: Failed to log prediction to SQLite: {e}")

        return response

    def predict_batch(self, incidents: List[schemas.IncidentInput]) -> List[schemas.PredictionResponse]:
        """Run batch inference efficiently."""
        self.ensure_loaded()
        if self.pipeline is None:
            raise RuntimeError("Model pipeline is not loaded.")

        if not incidents:
            return []

        # For batch, compute predictions row by row using predict to generate full responses & logs
        return [self.predict(inc) for inc in incidents]
