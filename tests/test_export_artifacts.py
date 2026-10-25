"""Tests for artifact-export prerequisite validation."""
import pytest

from src import config, export_artifacts


def test_export_prerequisites_report_missing_notebook_outputs(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "RAW_FILE", tmp_path / "incident_event_log.csv")
    monkeypatch.setattr(config, "INCIDENT_FILE", tmp_path / "incident_table.csv")
    monkeypatch.setattr(config, "NO_TARGET_FILE", tmp_path / "incidents_without_target.csv")
    monkeypatch.setattr(config, "TABLES_DIR", tmp_path / "tables")

    with pytest.raises(FileNotFoundError) as error:
        export_artifacts.validate_export_inputs()

    message = str(error.value)
    assert "notebooks 03, 05, and 06" in message
    assert "incident_table.csv" in message
    assert "model_comparison_validation.csv" in message
    assert "model_comparison_tuned.csv" in message
    assert "you do not need to run this export command" in message


def test_export_prerequisites_pass_when_all_inputs_exist(tmp_path, monkeypatch):
    raw_file = tmp_path / "incident_event_log.csv"
    incident_file = tmp_path / "incident_table.csv"
    no_target_file = tmp_path / "incidents_without_target.csv"
    tables_dir = tmp_path / "tables"
    tables_dir.mkdir()
    validation_comparison = tables_dir / "model_comparison_validation.csv"
    tuned_comparison = tables_dir / "model_comparison_tuned.csv"

    for path in (raw_file, incident_file, no_target_file, validation_comparison, tuned_comparison):
        path.touch()

    monkeypatch.setattr(config, "RAW_FILE", raw_file)
    monkeypatch.setattr(config, "INCIDENT_FILE", incident_file)
    monkeypatch.setattr(config, "NO_TARGET_FILE", no_target_file)
    monkeypatch.setattr(config, "TABLES_DIR", tables_dir)

    export_artifacts.validate_export_inputs()
