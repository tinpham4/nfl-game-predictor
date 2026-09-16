"""Configuration shared by the prediction pipeline."""

from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FEATURE_NAMES = (
    "off_epa_diff",
    "def_epa_diff",
    "pace_diff",
    "rest_diff",
    "div_game",
)


@dataclass(frozen=True)
class PipelineConfig:
    """Values that define one reproducible pipeline run."""

    first_season: int = 2016
    last_season: int = 2026
    train_through: int = 2023
    form_window: int = 5
    minimum_form_games: int = 3
    data_directory: Path = PROJECT_ROOT / "data"

    def validate(self) -> None:
        if self.first_season > self.train_through:
            raise ValueError("first_season must not be after train_through")
        if self.train_through >= self.last_season:
            raise ValueError("train_through must be before last_season")
        if self.form_window < 1:
            raise ValueError("form_window must be at least 1")
        if not 1 <= self.minimum_form_games <= self.form_window:
            raise ValueError("minimum_form_games must be between 1 and form_window")
