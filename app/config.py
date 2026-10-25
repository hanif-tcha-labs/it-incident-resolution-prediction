"""Application configuration and file paths."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

ARTIFACTS_DIR = BASE_DIR / "artifacts"
MODEL_PATH = ARTIFACTS_DIR / "model" / "final_pipeline.joblib"
MODEL_CARD_PATH = ARTIFACTS_DIR / "model" / "model_card.json"
METRICS_DIR = ARTIFACTS_DIR / "metrics"
EDA_DIR = ARTIFACTS_DIR / "eda"
REPLAY_CSV_PATH = ARTIFACTS_DIR / "replay" / "test_incidents.csv"
OPTIONS_PATH = ARTIFACTS_DIR / "options.json"

DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "predictions.db"

STATIC_DIR = BASE_DIR / "app" / "static"
TEMPLATES_DIR = BASE_DIR / "app" / "templates"
