import numpy as np
import pandas as pd

from nfl_predictor.config import FEATURE_NAMES
from nfl_predictor.modeling import add_predictions, train_model


def make_games() -> pd.DataFrame:
    rows = []
    for index in range(40):
        season = 2023 if index < 24 else 2024
        strength = (index % 8 - 3.5) / 5
        home_won = int(strength + (0.15 if index % 3 else -0.15) > 0)
        rows.append({
            "game_id": f"g{index}",
            "season": season,
            "is_played": True,
            "home_won": home_won,
            "home_team": "HOME",
            "away_team": "AWAY",
            "result": 3 if home_won else -3,
            "off_epa_diff": strength,
            "def_epa_diff": -strength / 2,
            "pace_diff": float(index % 5),
            "rest_diff": float(index % 2),
            "div_game": index % 2,
        })
    return pd.DataFrame(rows)


def test_training_and_prediction_produce_valid_probabilities():
    games = make_games()
    trained = train_model(games, train_through=2023)
    predicted = add_predictions(games, trained)

    assert len(trained.train) == 24
    assert len(trained.test) == 16
    assert predicted["home_win_prob"].between(0, 1).all()
    assert predicted["confidence"].between(0.5, 1).all()
    assert set(trained.metrics) == {
        "accuracy", "baseline", "roc_auc", "log_loss", "confusion_matrix"
    }
    assert np.isfinite(trained.scaler.mean_).all()
    assert list(games[list(FEATURE_NAMES)].columns) == list(FEATURE_NAMES)
