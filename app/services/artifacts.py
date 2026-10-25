"""Service to load and cache JSON/CSV artifacts."""
import json
from pathlib import Path
from typing import Any, Dict

from app import config

_CACHE: Dict[str, Any] = {}


def load_json_artifact(relative_path: str) -> Any:
    """Load and cache a JSON artifact from the artifacts directory.

    Raises FileNotFoundError with a clear message if missing.
    """
    if relative_path in _CACHE:
        return _CACHE[relative_path]

    file_path = config.ARTIFACTS_DIR / relative_path
    if not file_path.exists():
        raise FileNotFoundError(
            f"Required project artifact '{relative_path}' is missing at {file_path}. "
            "Please run 'python -m src.export_artifacts' to generate all required artifacts."
        )

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            _CACHE[relative_path] = data
            return data
    except Exception as e:
        raise RuntimeError(f"Error loading artifact '{relative_path}': {e}") from e


def clear_cache():
    """Clear in-memory artifact cache."""
    _CACHE.clear()
