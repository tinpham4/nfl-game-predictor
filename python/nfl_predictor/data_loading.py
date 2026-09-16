"""Download and reduce nflverse source data."""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

from .validation import require_columns


SCHEDULE_COLUMNS = (
    "game_id",
    "season",
    "week",
    "gameday",
    "away_team",
    "home_team",
    "result",
    "away_score",
    "home_score",
    "spread_line",
    "div_game",
    "away_rest",
    "home_rest",
)
PBP_COLUMNS = ("game_id", "season", "posteam", "defteam", "play_type", "epa")
TEAM_COLUMNS = (
    "team_abbr",
    "team_name",
    "team_nick",
    "team_conf",
    "team_division",
    "team_color",
    "team_logo_espn",
)


def _nflreadpy():
    try:
        import nflreadpy as nfl
    except ImportError as exc:
        raise RuntimeError(
            "nflreadpy is required to rebuild data. Install requirements-dev.txt first."
        ) from exc
    return nfl


def load_schedules(first_season: int, last_season: int) -> pd.DataFrame:
    raw = _nflreadpy().load_schedules().to_pandas()
    require_columns(raw, (*SCHEDULE_COLUMNS, "game_type"), "nflverse schedules")
    schedules = raw[
        raw["game_type"].eq("REG")
        & raw["season"].between(first_season, last_season)
    ][list(SCHEDULE_COLUMNS)].copy()
    schedules["gameday"] = pd.to_datetime(schedules["gameday"], errors="raise")
    schedules["is_played"] = schedules["result"].notna()
    return schedules


def load_play_by_play(seasons: Iterable[int]) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    nfl = _nflreadpy()
    for season in seasons:
        raw = nfl.load_pbp(seasons=[int(season)]).to_pandas()
        require_columns(raw, PBP_COLUMNS, f"{season} play-by-play")
        frames.append(raw[list(PBP_COLUMNS)].copy())
        print(f"  {season} loaded")
    if not frames:
        raise ValueError("No played seasons were available for play-by-play loading")
    return pd.concat(frames, ignore_index=True)


def load_teams(active_teams: Iterable[str]) -> pd.DataFrame:
    raw = _nflreadpy().load_teams().to_pandas()
    require_columns(raw, TEAM_COLUMNS, "nflverse teams")
    teams = raw[list(TEAM_COLUMNS)].copy()
    return teams[teams["team_abbr"].isin(set(active_teams))].reset_index(drop=True)
