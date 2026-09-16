# NFL Game Predictor

A Streamlit application that predicts straight-up NFL winners with an
explainable logistic regression model. The app is intentionally Python-only:
the data pipeline creates validated CSV/JSON artifacts, and Streamlit reads
those files without retraining the model during page loads.

**Live app:** [Open the NFL Game Predictor](https://nfl-game-predictor-snhqz6kcp4w37t87y4kgnk.streamlit.app/)

The current model is **66.2% accurate on 559 chronologically held-out games**
from 2024 through Week 1 of 2026, compared with a 53.8% always-pick-the-home-team
baseline. Its ROC AUC is 0.714.

## Architecture

```text
nflverse data
     |
     v
Python feature pipeline
     |
     v
Logistic regression
     |
     v
Validated CSV / JSON artifacts
     |
     v
Streamlit dashboard
```

The slow pipeline runs only when predictions need to be refreshed. The
generated artifacts are committed so the dashboard starts quickly locally and
on Streamlit Community Cloud.

## Project structure

```text
app.py                        Streamlit dashboard
.streamlit/config.toml        Streamlit theme and server settings
python/build_data.py          Pipeline command-line entry point
python/nfl_predictor/
  config.py                   Reproducible pipeline settings
  data_loading.py             nflverse downloads and column selection
  features.py                 Team-game statistics and rolling form
  modeling.py                 Training, evaluation, and prediction
  pipeline.py                 End-to-end orchestration and exports
  validation.py               Artifact contract checks
  dashboard.py                Dashboard data and standings helpers
tests/python/                 Python and Streamlit tests
data/                         Generated artifacts and their contract
```

## How the model works

The target is whether the home team wins. Each numeric input is expressed as
the home team's value minus the away team's value:

- offensive EPA per play over the previous five games
- defensive EPA per play allowed over the previous five games
- offensive plays per game over the previous five games
- rest-day difference
- whether the teams are in the same division
- pregame Elo rating difference based only on earlier results

The model is a scikit-learn logistic regression. That keeps every coefficient
and probability explainable while still outperforming the home-team baseline.

### Training and evaluation

- Training: 2016-2023, 1,966 games
- Held-out evaluation: 2024-2026 to date, 559 games
- Accuracy: 0.662
- Always-home baseline: 0.538
- ROC AUC: 0.714
- Log loss: 0.620
- Confusion matrix: 147 true negatives, 111 false positives, 78 false
  negatives, and 223 true positives

The split is chronological rather than random. That matches the real use case:
learn from past seasons and predict later games.

### Leakage prevention

Rolling form calls `shift(1)` before the rolling average, so a game's features
contain only information available before that game. The scaler is fit on the
training split only.

The original implementation also filled missing historical form with each
team's latest form. That inserted future information into early 2016 rows. The
current pipeline limits that fallback to unplayed games and drops historical
games without the required three prior games. A regression test protects this
boundary.

Elo is also point-in-time: each game's rating is recorded before that result
updates either team. Rating differences carry 67% of their value into a new
season, which moves teams toward the league average after offseason changes.

On the same 2024-2025 test set, removing the 42 contaminated training rows kept
accuracy at 63.17%, improved ROC AUC from 0.69320 to 0.69367, and improved log
loss from 0.63417 to 0.63408.

### Elo model improvement

Elo parameters were selected using 2021-2023 as a validation period inside the
training era. The 2024-2026 games remained the final evaluation set. Compared
with the same logistic regression without Elo:

| Metric | EPA-only model | EPA + Elo model |
|---|---:|---:|
| Accuracy | 0.630 | 0.662 |
| ROC AUC | 0.690 | 0.714 |
| Log loss | 0.636 | 0.620 |

The improved model remains a six-feature logistic regression; Elo adds a compact
measure of longer-term team strength instead of replacing the recent-form EPA
features.

## Dashboard

The Streamlit interface includes:

- team selector, logo, projected record, and league rank
- current offensive and defensive EPA with league ranks
- current pregame Elo and game-level Elo edges
- completed results and remaining schedule probabilities
- projected standings with conference filters
- weekly upcoming picks
- accuracy, baseline, ROC AUC, log loss, and confusion matrix
- confidence calibration and model coefficients
- held-out results and form history for every team

Projected standings combine actual wins from completed games with expected wins
from unplayed games. This is why projected records can contain decimals.

## Run locally

Python 3.11 or 3.12 is recommended.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501). The committed data is ready
to use, so running the dashboard does not require a pipeline rebuild.

## Rebuild predictions

Install the development dependencies, then run the offline pipeline:

```bash
source .venv/bin/activate
pip install -r requirements-dev.txt
python python/build_data.py
```

Useful options include `--last-season`, `--train-through`, `--form-window`,
`--minimum-form-games`, and the three `--elo-*` settings. Run
`python python/build_data.py --help` for details.

## Tests

```bash
source .venv/bin/activate
python -m pytest
```

The tests cover rolling features, leakage prevention, model training,
probability bounds, the artifact contract, generated exports, projected
standings, pregame Elo leakage protection, away-team probability conversion,
Streamlit startup, and team selection.

## Generated data contract

[`data/data_contract.json`](data/data_contract.json) lists every required CSV
column and JSON property. Both the pipeline and dashboard validate the
artifacts, including duplicate game IDs and probability ranges.

| File | Purpose |
|---|---|
| `predictions.csv` | Historical and upcoming games, probabilities, and features |
| `teams.csv` | Team names, conferences, divisions, colors, and logos |
| `team_form.csv` | Point-in-time team form history |
| `current_form.csv` | Each team's latest five-game form |
| `model_info.json` | Metrics, coefficients, confidence buckets, and limitations |

## Known limitations

- Injuries, starting-quarterback changes, weather, and roster moves are absent.
- Early-season form carries over from the previous season.
- Future games use the latest available form until the pipeline is rebuilt.
- The model predicts winners, not betting-spread results.

## Data source

Schedules, teams, and play-by-play come from
[nflverse](https://github.com/nflverse/nflverse-data) through
[`nflreadpy`](https://github.com/nflverse/nflreadpy).
