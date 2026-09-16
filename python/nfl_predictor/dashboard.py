"""Data-loading and presentation helpers for the Streamlit dashboard."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .validation import validate_output_files


@dataclass(frozen=True)
class DashboardData:
    predictions: pd.DataFrame
    teams: pd.DataFrame
    form_history: pd.DataFrame
    current_form: pd.DataFrame
    model_info: dict


def load_dashboard_data(data_directory: Path) -> DashboardData:
    """Load generated artifacts only after validating their contract."""

    validate_output_files(data_directory)
    predictions = pd.read_csv(data_directory / "predictions.csv")
    predictions["gameday"] = pd.to_datetime(predictions["gameday"])
    form_history = pd.read_csv(data_directory / "team_form.csv")
    form_history["gameday"] = pd.to_datetime(form_history["gameday"])

    return DashboardData(
        predictions=predictions,
        teams=pd.read_csv(data_directory / "teams.csv"),
        form_history=form_history,
        current_form=pd.read_csv(data_directory / "current_form.csv"),
        model_info=json.loads(
            (data_directory / "model_info.json").read_text(encoding="utf-8")
        ),
    )


def games_for_team(frame: pd.DataFrame, team: str) -> pd.DataFrame:
    """Return games where ``team`` appears on either side of the matchup."""

    return frame[(frame["home_team"] == team) | (frame["away_team"] == team)].copy()


def add_team_view(frame: pd.DataFrame, team: str) -> pd.DataFrame:
    """Express home-oriented game rows from the selected team's perspective."""

    result = frame.copy()
    result["is_home"] = result["home_team"] == team
    result["opponent"] = result["away_team"].where(
        result["is_home"], result["home_team"]
    )
    result["site"] = result["is_home"].map({True: "vs", False: "at"})
    result["team_win_prob"] = result["home_win_prob"].where(
        result["is_home"], 1 - result["home_win_prob"]
    )
    return result


def add_form_ranks(current_form: pd.DataFrame) -> pd.DataFrame:
    """Add league ranks, accounting for lower defensive EPA being better."""

    ranked = current_form.copy()
    ranked["off_rank"] = ranked["form_off_epa"].rank(
        ascending=False, method="min"
    ).astype(int)
    ranked["def_rank"] = ranked["form_def_epa"].rank(
        ascending=True, method="min"
    ).astype(int)
    return ranked


def projected_standings(
    predictions: pd.DataFrame, teams: pd.DataFrame, season: int
) -> pd.DataFrame:
    """Combine actual wins with expected wins from remaining games."""

    games = predictions[predictions["season"] == season].copy()
    if games.empty:
        return pd.DataFrame()

    played = games[games["is_played"]]
    upcoming = games[~games["is_played"]]
    actual_wins = played["actual_winner"].value_counts()
    home_expected = upcoming.groupby("home_team")["home_win_prob"].sum()
    away_expected = upcoming.groupby("away_team")["home_win_prob"].apply(
        lambda values: (1 - values).sum()
    )
    expected_remaining = home_expected.add(away_expected, fill_value=0)
    scheduled = pd.concat([games["home_team"], games["away_team"]]).value_counts()
    completed = pd.concat([played["home_team"], played["away_team"]]).value_counts()

    rows = []
    for team in teams["team_abbr"]:
        total_games = int(scheduled.get(team, 0))
        wins = int(actual_wins.get(team, 0))
        expected = float(expected_remaining.get(team, 0))
        projected_wins = wins + expected
        rows.append(
            {
                "team_abbr": team,
                "actual_wins": wins,
                "completed_games": int(completed.get(team, 0)),
                "expected_remaining_wins": expected,
                "games": total_games,
                "projected_wins": projected_wins,
                "projected_losses": total_games - projected_wins,
            }
        )

    standings = pd.DataFrame(rows).merge(teams, on="team_abbr", how="left")
    standings = standings.sort_values(
        ["projected_wins", "team_name"], ascending=[False, True]
    ).reset_index(drop=True)
    standings["rank"] = standings.index + 1
    return standings


def evaluation_games(predictions: pd.DataFrame, train_seasons: str) -> pd.DataFrame:
    """Return played games strictly after the final training season."""

    train_through = int(train_seasons.split("-")[-1])
    return predictions[
        predictions["is_played"] & (predictions["season"] > train_through)
    ].copy()
