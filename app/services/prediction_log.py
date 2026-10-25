"""SQLite logging service for tracking model predictions."""
import json
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional
from app import config


def get_db_connection() -> sqlite3.Connection:
    """Get SQLite database connection with row factory."""
    conn = sqlite3.connect(str(config.DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize predictions table."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                opened_at TEXT NOT NULL,
                inputs TEXT NOT NULL,
                predicted_hours REAL NOT NULL,
                output TEXT NOT NULL,
                model_version TEXT NOT NULL,
                has_warnings INTEGER NOT NULL
            )
        """)
        conn.commit()
    finally:
        conn.close()


def log_prediction(
    request_id: str,
    opened_at: str,
    inputs: Dict[str, Any],
    predicted_hours: float,
    output: Dict[str, Any],
    model_version: str,
    has_warnings: bool,
):
    """Log an individual prediction to SQLite."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO predictions (
                id, timestamp, opened_at, inputs, predicted_hours, output, model_version, has_warnings
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                request_id,
                datetime.now().isoformat(),
                opened_at,
                json.dumps(inputs, default=str),
                predicted_hours,
                json.dumps(output, default=str),
                model_version,
                1 if has_warnings else 0,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def get_prediction_summary() -> Dict[str, Any]:
    """Calculate summary statistics from logged predictions."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM predictions")
        total_count = cursor.fetchone()[0]

        if total_count == 0:
            return {
                "total_predictions": 0,
                "warning_rate_pct": 0.0,
                "median_predicted_hours": None,
                "mean_predicted_hours": None,
                "duration_distribution": {},
                "recent_drift_metrics": {
                    "unseen_assignment_group_rate_pct": 0.0,
                    "unseen_category_rate_pct": 0.0,
                    "reference_test_rate_pct": 0.5,
                },
            }

        cursor.execute("SELECT COUNT(*) FROM predictions WHERE has_warnings = 1")
        warning_count = cursor.fetchone()[0]

        cursor.execute("SELECT predicted_hours, inputs FROM predictions ORDER BY timestamp DESC LIMIT 500")
        rows = cursor.fetchall()
        hours = [r[0] for r in rows]

        # Count unknown assignment_group and category in recent requests
        unseen_group_count = 0
        unseen_cat_count = 0
        for r in rows:
            inp = json.loads(r[1])
            # Check warnings in output
            pass

        # Duration buckets
        buckets = {
            "under_1h": sum(1 for h in hours if h < 1.0),
            "1_to_24h": sum(1 for h in hours if 1.0 <= h < 24.0),
            "over_24h": sum(1 for h in hours if h >= 24.0),
        }

        # Calculate median and mean
        hours_sorted = sorted(hours)
        n = len(hours_sorted)
        med = hours_sorted[n // 2] if n % 2 != 0 else (hours_sorted[n // 2 - 1] + hours_sorted[n // 2]) / 2

        return {
            "total_predictions": total_count,
            "recent_sample_size": len(rows),
            "warning_rate_pct": round(warning_count / total_count * 100, 2),
            "median_predicted_hours": round(float(med), 2),
            "mean_predicted_hours": round(float(sum(hours) / len(hours)), 2),
            "duration_distribution": buckets,
        }
    finally:
        conn.close()


def get_recent_predictions(limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieve the most recent predictions."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, timestamp, opened_at, inputs, predicted_hours, output, model_version, has_warnings
            FROM predictions
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = cursor.fetchall()
        return [
            {
                "id": r["id"],
                "timestamp": r["timestamp"],
                "opened_at": r["opened_at"],
                "inputs": json.loads(r["inputs"]),
                "predicted_hours": r["predicted_hours"],
                "output": json.loads(r["output"]),
                "model_version": r["model_version"],
                "has_warnings": bool(r["has_warnings"]),
            }
            for r in rows
        ]
    finally:
        conn.close()
