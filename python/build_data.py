"""Command-line entry point for rebuilding model artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path

from nfl_predictor.config import PipelineConfig
from nfl_predictor.pipeline import run_pipeline


def parse_args() -> argparse.Namespace:
    defaults = PipelineConfig()
    parser = argparse.ArgumentParser(description="Build NFL prediction data")
    parser.add_argument("--first-season", type=int, default=defaults.first_season)
    parser.add_argument("--last-season", type=int, default=defaults.last_season)
    parser.add_argument("--train-through", type=int, default=defaults.train_through)
    parser.add_argument("--form-window", type=int, default=defaults.form_window)
    parser.add_argument("--minimum-form-games", type=int, default=defaults.minimum_form_games)
    parser.add_argument("--data-directory", type=Path, default=defaults.data_directory)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = PipelineConfig(
        first_season=args.first_season,
        last_season=args.last_season,
        train_through=args.train_through,
        form_window=args.form_window,
        minimum_form_games=args.minimum_form_games,
        data_directory=args.data_directory,
    )
    info = run_pipeline(config)
    print("\nBuild complete")
    print(f"  Accuracy: {info['accuracy']:.3f}")
    print(f"  ROC AUC:  {info['roc_auc']:.3f}")
    print(f"  Outputs:  {config.data_directory.resolve()}")


if __name__ == "__main__":
    main()
