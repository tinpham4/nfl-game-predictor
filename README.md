# NFL Game Predictor

A small full-stack application that predicts straight-up NFL winners with an
explainable logistic regression model. Python builds the features and prediction
artifacts, Spring Boot validates and serves them through a REST API, and a
responsive HTML/CSS/JavaScript dashboard presents the results.

The current model is **63.0% accurate on 559 chronologically held-out games**
from 2024 through Week 1 of 2026, compared with a 53.8% always-pick-the-home-team
baseline. Its ROC AUC is 0.690.

## Architecture

```text
nflverse
    |
    v
Python Data Pipeline
    |
    v
Feature Engineering
    |
    v
Logistic Regression Model
    |
    v
CSV / JSON Prediction Data
    |
    v
Spring Boot REST API
    |
    v
HTML + CSS + JavaScript Dashboard
```

Python and Java have intentionally separate jobs. The Python model runs only
when the data is rebuilt. Spring Boot loads the resulting files once at startup;
it does not download play-by-play data or retrain the model when a visitor opens
the site.

## Project structure

```text
backend/                      Spring Boot REST API and Java tests
frontend/                     Static dashboard served by Spring Boot
python/
  build_data.py               Pipeline command-line entry point
  nfl_predictor/
    config.py                 Reproducible pipeline settings
    data_loading.py           nflverse downloads and column selection
    features.py               Team-game stats and rolling form
    modeling.py               Training, evaluation, and prediction
    pipeline.py               End-to-end orchestration and exports
    validation.py             Input/output contract checks
tests/python/                 Python unit and integration tests
data/                         Generated CSV/JSON artifacts and shared contract
```

## How the model works

The target is whether the home team wins. Each numeric feature is expressed as
the home team's value minus the away team's value:

- offensive EPA per play over the previous five games
- defensive EPA per play allowed over the previous five games
- offensive plays per game over the previous five games
- rest-day difference
- whether the teams are in the same division

The model is a scikit-learn logistic regression. It is deliberately simple:
each feature has one coefficient, the output is a probability, and the result
is explainable in an interview.

### Training and evaluation

- Training: 2016-2023 (1,966 games)
- Test: 2024-2026 to date (559 games)
- Accuracy: 0.630
- Always-home baseline: 0.538
- ROC AUC: 0.690
- Log loss: 0.636
- Confusion matrix: 136 true negatives, 122 false positives, 85 false
  negatives, and 216 true positives

The test split is chronological, not random. That imitates the real use case:
learn from past seasons and predict future games.

### Leakage prevention

Rolling team form uses `shift(1)` before the rolling average. A game's features
therefore contain only games played before it. The scaler is fit on training
data only.

The original project also filled every missing historical form value with the
team's latest form. That inserted 2025 knowledge into early 2016 rows. The
current pipeline restricts that fallback to unplayed games and drops historical
games that do not yet have the required three prior games. A focused regression
test protects this boundary.

In a controlled comparison on the same committed 2024-2025 test set, removing
the 42 contaminated training rows kept accuracy at 63.17%, improved ROC AUC from
0.69320 to 0.69367, and improved log loss from 0.63417 to 0.63408.

## Data contract

[`data/data_contract.json`](data/data_contract.json) lists the required columns
and JSON properties. Python validates every artifact after export. Spring Boot
validates the same contract at startup, parses every field it uses into a Java
type, rejects duplicate games and invalid probabilities, and fails with a clear
message if the files drift out of sync.

Generated files:

| File | Purpose |
|---|---|
| `predictions.csv` | Historical and upcoming games with probabilities and features |
| `teams.csv` | Team names, conferences, divisions, colors, and logos |
| `team_form.csv` | Point-in-time team form history |
| `current_form.csv` | Each team's latest five-game form |
| `model_info.json` | Metrics, coefficients, confidence buckets, and limitations |

## Run locally

Prerequisites:

- Python 3.11 or 3.12
- Java 17 or newer
- internet access for the first dependency install and for data rebuilds

### 1. Set up Python

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

The generated data is committed, so a rebuild is optional when you only want to
run the application.

### 2. Run the application

```bash
cd backend
./mvnw spring-boot:run
```

Open [http://localhost:8080](http://localhost:8080). The dashboard and API come
from the same Spring Boot process, so no separate frontend server is needed.

### 3. Rebuild predictions

From the repository root with the virtual environment active:

```bash
python python/build_data.py
```

Useful options include `--last-season`, `--train-through`, `--form-window`, and
`--minimum-form-games`. Run `python python/build_data.py --help` for the full
list. Restart Spring Boot after a rebuild because the backend intentionally
caches the artifacts at startup.

## API endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/health` | Load status and artifact counts |
| GET | `/api/teams` | All NFL teams |
| GET | `/api/teams/{team}` | Team, current form, and projected standing |
| GET | `/api/teams/{team}/games` | Team schedule; supports `season` and `played` |
| GET | `/api/teams/{team}/form` | Current rolling form and league ranks |
| GET | `/api/predictions` | Predictions; supports `season`, `week`, `played`, and `team` |
| GET | `/api/predictions/week/{week}` | Predictions for one week |
| GET | `/api/predictions/team/{team}` | Predictions for one team |
| GET | `/api/standings` | Projected records; optionally filter by `conference` |
| GET | `/api/model` | Complete model metadata |
| GET | `/api/model/performance` | Evaluation metrics and confidence buckets |

Errors use JSON with a timestamp, HTTP status, error name, useful message, and
request path. Unknown teams return 404; malformed parameters return 400.

## Tests and builds

Run Python tests:

```bash
source .venv/bin/activate
python -m pytest
```

Run Java tests and build the runnable JAR:

```bash
cd backend
./mvnw test
./mvnw clean package
```

The tests cover rolling feature generation, leakage prevention, model training,
probability bounds, generated files, duplicate games, the Python/Java contract,
application startup, REST endpoints, error responses, and standings math.

## Dashboard

The frontend includes:

- team selector, logo, full-season projected record, and league rank
- current offensive and defensive EPA with league ranks
- game-by-game schedules and selected-team win probability
- weekly league predictions and projected standings
- held-out accuracy, baseline, ROC AUC, and test sample size
- feature, confidence-bucket, methodology, and limitation explanations
- loading and API error states, with mobile-friendly layouts

## Known limitations

- Injuries, starting-quarterback changes, weather, and roster moves are absent.
- Early-season form carries over from the prior season.
- Future games share the latest available form until the pipeline is rebuilt.
- The model predicts winners, not betting-spread results.
- Projected wins add actual wins to expected future wins. They are estimates,
  so projected records can contain decimals.

## Data source

Schedules, teams, and play-by-play come from
[nflverse](https://github.com/nflverse/nflverse-data) through
[`nflreadpy`](https://github.com/nflverse/nflreadpy).
