import pandas as pd

from nfl_predictor.dashboard import (
    add_form_ranks,
    add_team_view,
    evaluation_games,
    projected_standings,
)


def test_projected_standings_use_actual_wins_and_future_probabilities():
    predictions = pd.DataFrame(
        [
            {
                "season": 2026,
                "home_team": "A",
                "away_team": "B",
                "is_played": True,
                "actual_winner": "B",
                "home_win_prob": 0.9,
            },
            {
                "season": 2026,
                "home_team": "A",
                "away_team": "B",
                "is_played": False,
                "actual_winner": None,
                "home_win_prob": 0.6,
            },
        ]
    )
    teams = pd.DataFrame(
        {
            "team_abbr": ["A", "B"],
            "team_name": ["Alpha", "Beta"],
            "team_conf": ["AFC", "NFC"],
            "team_division": ["AFC Test", "NFC Test"],
        }
    )

    standings = projected_standings(predictions, teams, 2026).set_index("team_abbr")

    assert standings.loc["A", "actual_wins"] == 0
    assert standings.loc["A", "projected_wins"] == 0.6
    assert standings.loc["B", "actual_wins"] == 1
    assert standings.loc["B", "projected_wins"] == 1.4


def test_away_team_view_inverts_home_probability():
    game = pd.DataFrame(
        {"home_team": ["A"], "away_team": ["B"], "home_win_prob": [0.65]}
    )

    result = add_team_view(game, "B").iloc[0]

    assert result["opponent"] == "A"
    assert result["site"] == "at"
    assert result["team_win_prob"] == 0.35


def test_form_ranks_treat_lower_defensive_epa_as_better():
    form = pd.DataFrame(
        {
            "team": ["A", "B"],
            "form_off_epa": [0.2, 0.1],
            "form_def_epa": [-0.1, 0.05],
        }
    )

    ranked = add_form_ranks(form).set_index("team")

    assert ranked.loc["A", "off_rank"] == 1
    assert ranked.loc["A", "def_rank"] == 1


def test_evaluation_games_exclude_training_seasons_and_future_games():
    predictions = pd.DataFrame(
        {
            "season": [2023, 2024, 2026],
            "is_played": [True, True, False],
        }
    )

    result = evaluation_games(predictions, "2016-2023")

    assert result["season"].tolist() == [2024]
