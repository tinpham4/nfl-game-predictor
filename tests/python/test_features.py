import pandas as pd

from nfl_predictor.features import (
    add_pregame_elo,
    add_rolling_form,
    assemble_game_features,
)


def test_rolling_form_uses_only_prior_games():
    games = pd.DataFrame({
        "game_id": ["g1", "g2", "g3"],
        "season": [2024, 2024, 2024],
        "week": [1, 2, 3],
        "gameday": pd.to_datetime(["2024-09-01", "2024-09-08", "2024-09-15"]),
        "team": ["AAA", "AAA", "AAA"],
        "off_epa": [0.1, 0.3, 0.9],
        "def_epa": [-0.1, -0.3, -0.9],
        "plays": [60, 70, 80],
    })

    result = add_rolling_form(games, window=2, minimum_games=1)

    assert pd.isna(result.loc[0, "form_off_epa"])
    assert result.loc[1, "form_off_epa"] == 0.1
    assert result.loc[2, "form_off_epa"] == 0.2
    assert result.loc[2, "form_plays"] == 65


def test_elo_feature_is_recorded_before_the_current_result():
    schedules = pd.DataFrame(
        {
            "game_id": ["g1", "g2", "g3"],
            "season": [2024, 2024, 2025],
            "gameday": pd.to_datetime(["2024-09-01", "2024-09-08", "2025-09-01"]),
            "home_team": ["AAA", "AAA", "AAA"],
            "away_team": ["BBB", "BBB", "BBB"],
            "result": [7.0, -3.0, None],
            "is_played": [True, True, False],
        }
    )

    result = add_pregame_elo(schedules, 30, 0.67, 55)
    reversed_first_result = schedules.copy()
    reversed_first_result.loc[0, "result"] = -7.0
    reversed_result = add_pregame_elo(reversed_first_result, 30, 0.67, 55)

    assert result.loc[0, "elo_diff"] == 0
    assert reversed_result.loc[0, "elo_diff"] == 0
    assert result.loc[1, "elo_diff"] > 0
    assert reversed_result.loc[1, "elo_diff"] < 0
    assert abs(result.loc[2, "elo_diff"]) < abs(result.loc[1, "elo_diff"])


def test_current_form_fallback_is_never_applied_to_played_games():
    schedules = pd.DataFrame({
        "game_id": ["old", "future"],
        "season": [2016, 2026],
        "week": [1, 1],
        "gameday": pd.to_datetime(["2016-09-01", "2026-09-01"]),
        "away_team": ["AAA", "AAA"],
        "home_team": ["BBB", "BBB"],
        "result": [3.0, None],
        "away_score": [20.0, None],
        "home_score": [23.0, None],
        "spread_line": [1.5, None],
        "div_game": [0, 0],
        "away_rest": [7, 7],
        "home_rest": [7, 7],
        "is_played": [True, False],
        "elo_diff": [0.0, 10.0],
    })
    historical_form = pd.DataFrame({
        "game_id": ["old", "old"],
        "team": ["AAA", "BBB"],
        "form_off_epa": [None, None],
        "form_def_epa": [None, None],
        "form_plays": [None, None],
    })
    current = pd.DataFrame({
        "team": ["AAA", "BBB"],
        "form_off_epa": [0.2, 0.4],
        "form_def_epa": [-0.1, 0.1],
        "form_plays": [60.0, 65.0],
    })

    result = assemble_game_features(schedules, historical_form, current)

    assert result["game_id"].tolist() == ["future"]
    assert result.loc[0, "home_off_epa"] == 0.4
    assert result.loc[0, "away_off_epa"] == 0.2
