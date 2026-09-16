"""Feature engineering for point-in-time NFL team form."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import FEATURE_NAMES
from .validation import DataValidationError, require_columns, require_unique


FORM_STATS = ("off_epa", "def_epa", "plays")


def build_team_games(play_by_play: pd.DataFrame, schedules: pd.DataFrame) -> pd.DataFrame:
    require_columns(
        play_by_play,
        ["game_id", "posteam", "defteam", "play_type", "epa"],
        "play-by-play",
    )
    plays = play_by_play[
        play_by_play["play_type"].isin(["pass", "run"])
        & play_by_play["epa"].notna()
        & play_by_play["posteam"].notna()
        & play_by_play["defteam"].notna()
    ].copy()
    if plays.empty:
        raise DataValidationError("Play-by-play contains no usable pass or run plays")

    offense = (
        plays.groupby(["game_id", "posteam"])
        .agg(off_epa=("epa", "mean"), plays=("epa", "size"))
        .reset_index()
        .rename(columns={"posteam": "team"})
    )
    defense = (
        plays.groupby(["game_id", "defteam"])
        .agg(def_epa=("epa", "mean"))
        .reset_index()
        .rename(columns={"defteam": "team"})
    )
    game_dates = schedules[["game_id", "season", "week", "gameday"]]
    team_games = offense.merge(defense, on=["game_id", "team"], how="inner")
    team_games = team_games.merge(game_dates, on="game_id", how="inner")
    team_games = team_games.sort_values(["team", "gameday", "game_id"]).reset_index(drop=True)
    require_unique(team_games, ["game_id", "team"], "team game statistics")
    return team_games


def add_rolling_form(
    team_games: pd.DataFrame, window: int, minimum_games: int
) -> pd.DataFrame:
    """Add averages of prior games; the current row is always excluded."""

    result = team_games.sort_values(["team", "gameday", "game_id"]).copy()
    for stat in FORM_STATS:
        shifted = result.groupby("team", sort=False)[stat].shift(1)
        rolled = shifted.groupby(result["team"], sort=False).rolling(
            window=window, min_periods=minimum_games
        ).mean()
        result[f"form_{stat}"] = rolled.reset_index(level=0, drop=True)
    return result


def build_current_form(team_games: pd.DataFrame, window: int) -> pd.DataFrame:
    recent = team_games.sort_values(["team", "gameday", "game_id"]).groupby(
        "team", sort=False
    ).tail(window)
    return recent.groupby("team", sort=True).agg(
        form_off_epa=("off_epa", "mean"),
        form_def_epa=("def_epa", "mean"),
        form_plays=("plays", "mean"),
        games_used=("off_epa", "size"),
        form_through=("gameday", "max"),
    ).reset_index()


def assemble_game_features(
    schedules: pd.DataFrame,
    team_games_with_form: pd.DataFrame,
    current_form: pd.DataFrame,
) -> pd.DataFrame:
    """Join point-in-time team form to games without leaking current form backward."""

    require_unique(schedules, ["game_id"], "schedules")
    form_columns = ["game_id", "team", "form_off_epa", "form_def_epa", "form_plays"]
    form = team_games_with_form[form_columns]
    require_unique(form, ["game_id", "team"], "rolling form")

    home_form = form.rename(columns={
        "team": "home_team",
        "form_off_epa": "home_off_epa",
        "form_def_epa": "home_def_epa",
        "form_plays": "home_plays",
    })
    away_form = form.rename(columns={
        "team": "away_team",
        "form_off_epa": "away_off_epa",
        "form_def_epa": "away_def_epa",
        "form_plays": "away_plays",
    })
    games = schedules.merge(home_form, on=["game_id", "home_team"], how="left")
    games = games.merge(away_form, on=["game_id", "away_team"], how="left")

    current_home = current_form.rename(columns={
        "team": "home_team",
        "form_off_epa": "current_home_off_epa",
        "form_def_epa": "current_home_def_epa",
        "form_plays": "current_home_plays",
    })
    current_away = current_form.rename(columns={
        "team": "away_team",
        "form_off_epa": "current_away_off_epa",
        "form_def_epa": "current_away_def_epa",
        "form_plays": "current_away_plays",
    })
    games = games.merge(
        current_home[["home_team", "current_home_off_epa", "current_home_def_epa", "current_home_plays"]],
        on="home_team",
        how="left",
    )
    games = games.merge(
        current_away[["away_team", "current_away_off_epa", "current_away_def_epa", "current_away_plays"]],
        on="away_team",
        how="left",
    )

    # Current form represents knowledge available at build time. It is valid for
    # future games, but using it to fill old games would leak future seasons.
    upcoming = ~games["is_played"]
    fallback_pairs = {
        "home_off_epa": "current_home_off_epa",
        "home_def_epa": "current_home_def_epa",
        "home_plays": "current_home_plays",
        "away_off_epa": "current_away_off_epa",
        "away_def_epa": "current_away_def_epa",
        "away_plays": "current_away_plays",
    }
    for feature, fallback in fallback_pairs.items():
        games.loc[upcoming, feature] = games.loc[upcoming, feature].fillna(
            games.loc[upcoming, fallback]
        )

    games["off_epa_diff"] = games["home_off_epa"] - games["away_off_epa"]
    games["def_epa_diff"] = games["home_def_epa"] - games["away_def_epa"]
    games["pace_diff"] = games["home_plays"] - games["away_plays"]
    games["rest_diff"] = games["home_rest"] - games["away_rest"]
    games["home_won"] = np.where(games["result"] > 0, 1, 0)

    missing_upcoming = games.loc[upcoming, list(FEATURE_NAMES)].isna().any(axis=1)
    if missing_upcoming.any():
        game_ids = games.loc[upcoming].loc[missing_upcoming, "game_id"].tolist()
        raise DataValidationError(
            "Upcoming games are missing model features: " + ", ".join(game_ids[:5])
        )

    cleaned = games.dropna(subset=list(FEATURE_NAMES)).copy()
    cleaned = cleaned[~(cleaned["is_played"] & cleaned["result"].eq(0))]
    cleaned = cleaned.drop(columns=list(fallback_pairs.values())).reset_index(drop=True)
    require_unique(cleaned, ["game_id"], "model games")
    return cleaned
