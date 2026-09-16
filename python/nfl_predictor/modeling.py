"""Training, evaluation, and prediction helpers."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, log_loss, roc_auc_score
from sklearn.preprocessing import StandardScaler

from .config import FEATURE_NAMES
from .validation import DataValidationError


@dataclass(frozen=True)
class TrainedModel:
    model: LogisticRegression
    scaler: StandardScaler
    train: pd.DataFrame
    test: pd.DataFrame
    metrics: dict


def train_model(games: pd.DataFrame, train_through: int) -> TrainedModel:
    played = games[games["is_played"]].copy()
    train = played[played["season"] <= train_through].copy()
    test = played[played["season"] > train_through].copy()
    if train.empty or test.empty:
        raise DataValidationError("Chronological split requires non-empty train and test sets")
    if train["home_won"].nunique() != 2 or test["home_won"].nunique() != 2:
        raise DataValidationError("Train and test sets must each contain home wins and losses")

    scaler = StandardScaler()
    train_features = scaler.fit_transform(train[list(FEATURE_NAMES)])
    test_features = scaler.transform(test[list(FEATURE_NAMES)])
    model = LogisticRegression(max_iter=1_000)
    model.fit(train_features, train["home_won"])

    probabilities = model.predict_proba(test_features)[:, 1]
    predictions = model.predict(test_features)
    tn, fp, fn, tp = confusion_matrix(test["home_won"], predictions).ravel()
    metrics = {
        "accuracy": float(accuracy_score(test["home_won"], predictions)),
        "baseline": float(test["home_won"].mean()),
        "roc_auc": float(roc_auc_score(test["home_won"], probabilities)),
        "log_loss": float(log_loss(test["home_won"], probabilities)),
        "confusion_matrix": {"true_negative": int(tn), "false_positive": int(fp), "false_negative": int(fn), "true_positive": int(tp)},
    }
    return TrainedModel(model=model, scaler=scaler, train=train, test=test, metrics=metrics)


def add_predictions(games: pd.DataFrame, trained: TrainedModel) -> pd.DataFrame:
    result = games.copy()
    transformed = trained.scaler.transform(result[list(FEATURE_NAMES)])
    result["home_win_prob"] = trained.model.predict_proba(transformed)[:, 1]
    if not result["home_win_prob"].between(0, 1).all():
        raise DataValidationError("Model produced a probability outside [0, 1]")
    result["predicted_winner"] = np.where(
        result["home_win_prob"] >= 0.5, result["home_team"], result["away_team"]
    )
    result["confidence"] = np.maximum(result["home_win_prob"], 1 - result["home_win_prob"])
    result["actual_winner"] = np.where(
        result["is_played"],
        np.where(result["result"] > 0, result["home_team"], result["away_team"]),
        None,
    )
    result["was_correct"] = result["predicted_winner"].eq(result["actual_winner"]).where(
        result["is_played"], None
    )
    return result


def confidence_buckets(predicted_games: pd.DataFrame, train_through: int) -> list[dict]:
    test = predicted_games[
        predicted_games["is_played"] & (predicted_games["season"] > train_through)
    ].copy()
    labels = ["50-55%", "55-60%", "60-65%", "65-70%", "70%+"]
    test["bucket"] = pd.cut(
        test["confidence"],
        bins=[0.5, 0.55, 0.60, 0.65, 0.70, 1.0],
        labels=labels,
        include_lowest=True,
    )
    summary = test.groupby("bucket", observed=False).agg(
        games=("was_correct", "size"),
        accuracy=("was_correct", "mean"),
        average_confidence=("confidence", "mean"),
    )
    records = summary.reset_index().to_dict(orient="records")
    for record in records:
        record["bucket"] = str(record["bucket"])
        record["games"] = int(record["games"])
        for key in ("accuracy", "average_confidence"):
            record[key] = None if pd.isna(record[key]) else float(record[key])
    return records
