"""Validation helpers for raw inputs and generated artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import pandas as pd


class DataValidationError(ValueError):
    """Raised when input or output data does not meet the project contract."""


def require_columns(frame: pd.DataFrame, required: Iterable[str], source: str) -> None:
    missing = sorted(set(required) - set(frame.columns))
    if missing:
        raise DataValidationError(f"{source} is missing required columns: {', '.join(missing)}")


def require_unique(frame: pd.DataFrame, columns: list[str], source: str) -> None:
    duplicate_count = int(frame.duplicated(columns).sum())
    if duplicate_count:
        joined = ", ".join(columns)
        raise DataValidationError(
            f"{source} contains {duplicate_count} duplicate row(s) for key: {joined}"
        )


def load_contract(path: Path) -> dict:
    if not path.is_file():
        raise DataValidationError(f"Data contract not found: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DataValidationError(f"Data contract is not valid JSON: {exc}") from exc


def validate_output_files(data_directory: Path) -> None:
    """Check every generated artifact against the shared Python/Java contract."""

    contract = load_contract(data_directory / "data_contract.json")
    for filename, definition in contract["csvFiles"].items():
        path = data_directory / filename
        if not path.is_file():
            raise DataValidationError(f"Required output file not found: {path}")
        frame = pd.read_csv(path)
        require_columns(frame, definition["requiredColumns"], filename)

    info_path = data_directory / "model_info.json"
    if not info_path.is_file():
        raise DataValidationError(f"Required output file not found: {info_path}")
    try:
        info = json.loads(info_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DataValidationError(f"model_info.json is not valid JSON: {exc}") from exc

    missing = sorted(set(contract["jsonFiles"]["model_info.json"]["requiredProperties"]) - info.keys())
    if missing:
        raise DataValidationError(
            "model_info.json is missing required properties: " + ", ".join(missing)
        )

    predictions = pd.read_csv(data_directory / "predictions.csv")
    require_unique(predictions, ["game_id"], "predictions.csv")
    if not predictions["home_win_prob"].between(0, 1).all():
        raise DataValidationError("predictions.csv contains a home_win_prob outside [0, 1]")
    if not predictions["confidence"].between(0.5, 1).all():
        raise DataValidationError("predictions.csv contains a confidence outside [0.5, 1]")
