"""End-to-end orchestration for building prediction artifacts."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .config import FEATURE_NAMES, PipelineConfig
from .data_loading import load_play_by_play, load_schedules, load_teams
from .features import add_rolling_form, assemble_game_features, build_current_form, build_team_games
from .modeling import add_predictions, confidence_buckets, train_model
from .validation import validate_output_files


PREDICTION_COLUMNS = [
    "game_id", "season", "week", "gameday", "away_team", "home_team",
    "away_score", "home_score", "result", "spread_line", "div_game",
    "is_played", "home_win_prob", "predicted_winner", "confidence",
    "actual_winner", "was_correct", "home_off_epa", "home_def_epa",
    "home_plays", "away_off_epa", "away_def_epa", "away_plays",
    "off_epa_diff", "def_epa_diff", "pace_diff", "rest_diff",
]
TEAM_FORM_COLUMNS = [
    "game_id", "season", "week", "gameday", "team", "off_epa",
    "def_epa", "plays", "form_off_epa", "form_def_epa", "form_plays",
]


def export_outputs(
    predictions: pd.DataFrame,
    current_form: pd.DataFrame,
    team_games: pd.DataFrame,
    teams: pd.DataFrame,
    model_info: dict,
    data_directory: Path,
) -> None:
    data_directory.mkdir(parents=True, exist_ok=True)
    predictions[PREDICTION_COLUMNS].to_csv(data_directory / "predictions.csv", index=False)
    current_form.to_csv(data_directory / "current_form.csv", index=False)
    team_games[TEAM_FORM_COLUMNS].to_csv(data_directory / "team_form.csv", index=False)
    teams.to_csv(data_directory / "teams.csv", index=False)
    (data_directory / "model_info.json").write_text(
        json.dumps(model_info, indent=2) + "\n", encoding="utf-8"
    )
    validate_output_files(data_directory)


def run_pipeline(config: PipelineConfig) -> dict:
    config.validate()
    print("Loading schedules...")
    schedules = load_schedules(config.first_season, config.last_season)
    seasons = sorted(schedules.loc[schedules["is_played"], "season"].unique())
    print("Loading play-by-play...")
    play_by_play = load_play_by_play(seasons)
    print("Building point-in-time team form...")
    raw_team_games = build_team_games(play_by_play, schedules)
    team_games = add_rolling_form(
        raw_team_games, config.form_window, config.minimum_form_games
    )
    current_form = build_current_form(raw_team_games, config.form_window)
    games = assemble_game_features(schedules, team_games, current_form)

    print("Training logistic regression...")
    trained = train_model(games, config.train_through)
    predictions = add_predictions(games, trained)
    teams = load_teams(set(games["home_team"]) | set(games["away_team"]))
    coefficients = dict(zip(FEATURE_NAMES, trained.model.coef_[0].round(4).tolist()))
    info = {
        "built_on": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
        "train_seasons": f"{int(trained.train['season'].min())}-{config.train_through}",
        "test_seasons": f"{int(trained.test['season'].min())}-{int(trained.test['season'].max())}",
        "train_games": int(len(trained.train)),
        "test_games": int(len(trained.test)),
        **trained.metrics,
        "form_through": str(current_form["form_through"].max().date()),
        "upcoming_season": config.last_season,
        "form_window": config.form_window,
        "minimum_form_games": config.minimum_form_games,
        "features": list(FEATURE_NAMES),
        "coefficients": coefficients,
        "confidence_buckets": confidence_buckets(predictions, config.train_through),
        "limitations": [
            "The model does not account for injuries, weather, or roster changes.",
            "Early-season form carries over from the prior season.",
            "Predictions are straight-up winners, not betting-spread picks.",
        ],
    }
    export_outputs(predictions, current_form, team_games, teams, info, config.data_directory)
    return info
