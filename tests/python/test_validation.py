import json
import shutil
from pathlib import Path

import pandas as pd
import pytest

from nfl_predictor.pipeline import export_outputs
from nfl_predictor.validation import DataValidationError, require_columns, validate_output_files


def test_missing_required_column_has_clear_error():
    with pytest.raises(DataValidationError, match="missing required columns: season"):
        require_columns(pd.DataFrame({"game_id": ["g1"]}), ["game_id", "season"], "input")


def test_committed_outputs_match_shared_contract():
    validate_output_files(Path("data"))


def test_committed_elo_model_improves_all_held_out_metrics():
    info = json.loads(Path("data/model_info.json").read_text())
    comparison = info["model_comparison"]

    assert comparison["accuracy_after"] > comparison["accuracy_before"]
    assert comparison["roc_auc_after"] > comparison["roc_auc_before"]
    assert comparison["log_loss_after"] < comparison["log_loss_before"]

    predictions = pd.read_csv("data/predictions.csv")
    train_through = int(info["train_seasons"].split("-")[-1])
    held_out = predictions[
        predictions["is_played"] & (predictions["season"] > train_through)
    ]
    assert held_out["was_correct"].eq(True).mean() == pytest.approx(info["accuracy"])


def test_export_creates_every_expected_output(tmp_path):
    source = Path("data")
    shutil.copyfile(source / "data_contract.json", tmp_path / "data_contract.json")
    predictions = pd.read_csv(source / "predictions.csv").head(4)
    current_form = pd.read_csv(source / "current_form.csv").head(2)
    team_form = pd.read_csv(source / "team_form.csv").head(4)
    teams = pd.read_csv(source / "teams.csv").head(2)
    model_info = json.loads((source / "model_info.json").read_text())

    export_outputs(
        predictions, current_form, team_form, teams, model_info, tmp_path
    )

    expected = {
        "predictions.csv", "current_form.csv", "team_form.csv",
        "teams.csv", "model_info.json", "data_contract.json"
    }
    assert {path.name for path in tmp_path.iterdir()} == expected


def test_duplicate_prediction_games_are_rejected(tmp_path):
    contract = json.loads(Path("data/data_contract.json").read_text())
    (tmp_path / "data_contract.json").write_text(json.dumps(contract))
    for filename, definition in contract["csvFiles"].items():
        row = {column: 0 for column in definition["requiredColumns"]}
        if filename == "predictions.csv":
            row.update({"game_id": "same", "home_win_prob": 0.6, "confidence": 0.6})
            pd.DataFrame([row, row]).to_csv(tmp_path / filename, index=False)
        else:
            pd.DataFrame([row]).to_csv(tmp_path / filename, index=False)
    info = {key: 0 for key in contract["jsonFiles"]["model_info.json"]["requiredProperties"]}
    (tmp_path / "model_info.json").write_text(json.dumps(info))

    with pytest.raises(DataValidationError, match="duplicate"):
        validate_output_files(tmp_path)
