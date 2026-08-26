# NFL Game Predictor

A Streamlit app that predicts NFL winners from team efficiency data, and shows
its own track record so you can judge whether to believe it.

Pick any team from the sidebar and you get their projected record, their
game-by-game picks for the upcoming season, and every prediction the model made
on games it was never trained on, next to what actually happened.

**Accuracy: 63.2% on 543 unseen games**, against a 53.6% baseline of just always
picking the home team.

---

## What's in here

| File | What it does |
|---|---|
| `build_data.py` | Downloads the data, builds the features, trains the model, saves the results |
| `app.py` | The Streamlit app - reads the saved results and puts them on screen |
| `data/` | The trained model's output, as CSVs. Committed, so the app runs anywhere. |
| `requirements.txt` | What the app needs to **run** |
| `requirements-dev.txt` | What you need to **rebuild** the data |
| `DEPLOY.md` | Step-by-step for putting it online |

The two-file split is deliberate. `build_data.py` does the slow work once -
downloading ~345,000 plays and training the model - and writes small CSVs.
`app.py` only reads those. Without the split, the app would re-download ten
seasons of nflverse data on every single widget click.

## Running it

```bash
pip install -r requirements.txt
streamlit run app.py
```

That's it. The `data/` folder is committed, so you don't need to rebuild
anything to look at the app.

## Rebuilding the data

Do this to refresh predictions once real games have been played:

```bash
pip install -r requirements-dev.txt
python build_data.py        # a couple of minutes, downloads ~10 seasons
streamlit run app.py
```

The app checks for the CSVs on startup and tells you to run `build_data.py` if
they're missing, rather than crashing.

## Deploying it

See `DEPLOY.md`. Short version: push to GitHub, point Streamlit Community Cloud
at `app.py`, done - it's free and gives you a public URL.

## How the model works

**Data.** Ten seasons of nflverse play-by-play (2016-2025), regular season only.
About 345,000 plays, rolled up into 5,522 team-games.

**Features.** Four numbers describe a team's current form, each a rolling average
of their last 5 games:

- offensive EPA per play
- defensive EPA per play allowed
- pace (offensive plays run per game)
- rest days

Plus whether it's a division game. Every feature enters the model as a
difference: the home team's number minus the away team's. So a positive
offensive EPA difference means the home team has the better offense right now.

**Model.** Logistic regression. Trained on 2016-2023 (2,008 games), tested on
2024-2025 (543 games).

**Target.** Does the home team win, straight up.

### The leakage guards

This is the part I'd want to be asked about. A form model is very easy to break
in a way that makes it look great and be worthless:

- `.shift(1)` before the rolling average, so a team's form entering a game never
  includes that game's own result.
- **Split by season, not randomly.** A random split would let the model train on
  December games and be tested on September games from the same year, which is
  time travel. Training on the past and testing on the future is the only split
  that tells you what you'd actually get.
- **Scaler fit on training data only**, so the test set stays genuinely unseen.
- Ties dropped rather than forced into a win or a loss.

### What it learned

| Feature | Coefficient |
|---|---|
| off_epa_diff | +0.554 |
| rest_diff | +0.068 |
| pace_diff | +0.020 |
| div_game | -0.031 |
| def_epa_diff | -0.263 |

Positive pushes the prediction toward the home team. Offense dominates, defense
is second, and the signs match football logic - which is the reassuring part. The
model landed on something sensible on its own rather than latching onto
something weird.

### Is the confidence real?

Overall accuracy doesn't tell you whether a model knows when it's guessing. So I
bucketed the test games by how confident the model was:

| Confidence | Games | Accuracy |
|---|---|---|
| 50-55% | 122 | 48% |
| 55-60% | 113 | 59% |
| 60-65% | 103 | 63% |
| 65-70% | 71 | 69% |
| 70%+ | 134 | 78% |

It climbs cleanly, and the numbers land close to the confidence levels
themselves. That means the probability the app shows is meaningful, not just a
number between 0 and 1 - a 70% pick really does come in about 70% of the time.

## Projecting a season record

The app projects records by **adding up win probabilities**, not by counting how
many games the model picked a team to win.

That distinction matters. If a team's form makes them a slight favorite in all 17
games, counting picks projects them 17-0, which is not remotely what the model
believes. Adding the probabilities gives about 11 wins, which is. Same model,
honest answer.

## Known limitations

- **No injuries.** A team that just lost its starting quarterback still looks
  exactly as good as it did last week. This is the single biggest gap.
- **Form is frozen between rebuilds.** Right now every 2026 game is predicted off
  how teams finished 2025. Re-run `build_data.py` during the season and the
  predictions update themselves off real results.
- **Cross-season carryover.** Week 1 form comes from the end of the previous
  season, which ignores the offseason. It's an imperfect assumption, but the
  alternative was having no predictions at all for the first three weeks.
- **It does not beat the spread.** I tested that separately and got 49.3%, below
  the 52.4% break-even at standard odds. The betting market has this data priced
  in already. This app predicts who wins, not who covers.

## Next things to try

- Injury data, especially quarterback availability
- Opponent-adjusted EPA, so beating up a bad defense counts for less
- Weather (`temp`, `wind`, `roof` are already on the schedule table)
- Regularization plus time-series cross-validation instead of one fixed split

## Data source

[nflverse](https://github.com/nflverse/nflverse-data) via
[`nflreadpy`](https://github.com/nflverse/nflreadpy).

Note: this uses `nflreadpy`, not the older `nfl_data_py`. That one is deprecated
and pins pandas 1.5.3, which breaks a modern environment. `nflreadpy` returns
polars, so everything gets `.to_pandas()` right after loading.
