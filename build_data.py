# build_data.py
#
# This script does all the slow work up front: it downloads the nflverse data,
# builds my team form features, trains the logistic regression model, and then
# saves everything the Streamlit app needs as small CSV files.
#
# I split it out from the app on purpose. Downloading ten seasons of play-by-play
# takes a couple of minutes, and I don't want the app doing that every time
# somebody clicks a button. So: run this once, then run the app.
#
# Usage:  python build_data.py

import os
import json
import numpy as np
import pandas as pd
import nflreadpy as nfl


# I keep the outputs in a data folder next to this script so the app always
# knows where to look, no matter what directory you launch it from.
HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")

FIRST_SEASON = 2016
LAST_SEASON = 2026          # the upcoming season - schedule is posted, no results yet
TRAIN_THROUGH = 2023        # everything up to and including this year trains the model
FORM_WINDOW = 5             # I average each team's last 5 games to describe their form
MIN_GAMES = 3               # but I need at least 3 games of history before I trust it


print("=" * 60)
print("NFL game predictor - building data")
print("=" * 60)


# ---------------------------------------------------------------------------
# Part 1: the schedule
# ---------------------------------------------------------------------------
# The schedule table is the backbone of everything. One row per game, and it
# already carries the things I'd otherwise have to compute myself: rest days,
# whether it's a division game, and the Vegas spread.

print("")
print("Loading schedules...")

schedules = nfl.load_schedules().to_pandas()

# Regular season only. Playoff games have different rest patterns and a much
# smaller sample, so mixing them in would just add noise.
schedules = schedules[schedules["game_type"] == "REG"]
schedules = schedules[schedules["season"] >= FIRST_SEASON]
schedules = schedules[schedules["season"] <= LAST_SEASON]

keep_cols = ["game_id", "season", "week", "gameday", "away_team", "home_team",
             "result", "away_score", "home_score", "spread_line", "div_game",
             "away_rest", "home_rest"]
schedules = schedules[keep_cols].copy()
schedules["gameday"] = pd.to_datetime(schedules["gameday"])

# A game is "played" if it has a final score. Everything else is upcoming.
schedules["is_played"] = schedules["result"].notna()

print("Total regular season games loaded: " + str(len(schedules)))
print("Games already played: " + str(schedules["is_played"].sum()))
print("Games still upcoming: " + str((~schedules["is_played"]).sum()))


# ---------------------------------------------------------------------------
# Part 2: team stats from play-by-play
# ---------------------------------------------------------------------------
# I want three things per team per game: how efficient their offense was, how
# efficient their defense was, and how fast they played. EPA (expected points
# added) is the standard efficiency stat, and pace I just measure as the number
# of plays the offense ran.
#
# Play-by-play is huge - about 370 columns and 50k rows per season - so I load
# one season at a time and immediately throw away every column I don't need.
# Loading all ten at once would eat several gigs of memory.

print("")
print("Loading play-by-play (this is the slow part, give it a minute)...")

pbp_cols = ["game_id", "season", "posteam", "defteam", "play_type", "epa"]
season_frames = []

seasons_with_games = sorted(schedules[schedules["is_played"]]["season"].unique())

for season in seasons_with_games:
    one_season = nfl.load_pbp(seasons=[int(season)]).to_pandas()
    one_season = one_season[pbp_cols]
    season_frames.append(one_season)
    print("  " + str(season) + " loaded")

pbp = pd.concat(season_frames, ignore_index=True)
season_frames = None   # let Python reclaim the memory

# I only want real offensive snaps. Kickoffs, punts, kneels and spikes all have
# EPA attached but they'd distort what I'm trying to measure.
pbp = pbp[pbp["play_type"].isin(["pass", "run"])]
pbp = pbp[pbp["epa"].notna()]
pbp = pbp[pbp["posteam"].notna()]
pbp = pbp[pbp["defteam"].notna()]

print("Usable plays: " + str(len(pbp)))

# Offense: group by the team WITH the ball.
offense = pbp.groupby(["game_id", "posteam"]).agg(
    off_epa=("epa", "mean"),
    plays=("epa", "size")
).reset_index()
offense = offense.rename(columns={"posteam": "team"})

# Defense: group by the team DEFENDING. Same EPA numbers, opposite point of
# view. Lower is better here, since it's points allowed per play.
defense = pbp.groupby(["game_id", "defteam"]).agg(
    def_epa=("epa", "mean")
).reset_index()
defense = defense.rename(columns={"defteam": "team"})

team_games = pd.merge(offense, defense, on=["game_id", "team"], how="inner")

print("Team-game rows built: " + str(len(team_games)))


# ---------------------------------------------------------------------------
# Part 3: turning raw stats into "form"
# ---------------------------------------------------------------------------
# This is the part that matters most, and it's the easiest place to cheat by
# accident. What I want for every game is: what did this team look like going
# INTO this game. Not including it. If I let a team's own performance in a game
# leak into the features predicting that game, the model looks amazing and is
# completely useless.
#
# The .shift(1) is what prevents that. It pushes every team's stats forward one
# game, so the rolling average only ever sees games that already happened.

print("")
print("Building rolling form features...")

# I need the date on each team-game row so I can sort them chronologically.
game_dates = schedules[["game_id", "season", "week", "gameday"]]
team_games = pd.merge(team_games, game_dates, on="game_id", how="inner")
team_games = team_games.sort_values(["team", "gameday"]).reset_index(drop=True)

# Note that I deliberately do NOT restart the average at the start of each
# season. That means a team's week 1 form comes from how they finished the
# previous year. It's an imperfect assumption - rosters change over the
# offseason - but it's a lot better than having no prediction at all for the
# first three weeks, and it means the app can predict opening weekend.

stat_names = ["off_epa", "def_epa", "plays"]

for stat in stat_names:
    shifted = team_games.groupby("team")[stat].shift(1)
    rolled = shifted.groupby(team_games["team"]).rolling(
        window=FORM_WINDOW, min_periods=MIN_GAMES
    ).mean()
    # rolling on a groupby gives back a multi-index, so I drop the team level
    # to line it back up with the original rows
    team_games["form_" + stat] = rolled.reset_index(level=0, drop=True)

form_cols = ["game_id", "team", "form_off_epa", "form_def_epa", "form_plays"]
form = team_games[form_cols].copy()

print("Form rows with enough history: " + str(form["form_off_epa"].notna().sum()))


# ---------------------------------------------------------------------------
# Part 4: current form, for games that haven't happened yet
# ---------------------------------------------------------------------------
# The rolling table above only covers games that were actually played. For an
# upcoming game there's no row, so I need each team's form as of right now:
# the average of their last few completed games.
#
# Nice side effect - this updates itself. Right now every 2026 game gets
# predicted off how teams finished 2025. Once week 1 is in the books and I
# re-run this script, week 2's predictions will use real 2026 games instead.

print("")
print("Computing current team form...")

recent = team_games.sort_values(["team", "gameday"]).groupby("team").tail(FORM_WINDOW)

current_form = recent.groupby("team").agg(
    form_off_epa=("off_epa", "mean"),
    form_def_epa=("def_epa", "mean"),
    form_plays=("plays", "mean"),
    games_used=("off_epa", "size"),
    form_through=("gameday", "max")
).reset_index()

print("Teams with current form: " + str(len(current_form)))
print("Form is current through: " + str(current_form["form_through"].max().date()))


# ---------------------------------------------------------------------------
# Part 5: one row per game, home minus away
# ---------------------------------------------------------------------------
# The model predicts one thing: does the home team win. So every feature is
# expressed as a difference - home team's number minus away team's number.
# A positive offensive EPA difference means the home team has the better
# offense right now. That makes the coefficients easy to read later.

print("")
print("Assembling the game table...")

games = schedules.copy()

# For played games I look up the form from the rolling table (which knows the
# right point in time). For upcoming games I fall back to current form.

home_form = form.rename(columns={
    "team": "home_team",
    "form_off_epa": "home_off_epa",
    "form_def_epa": "home_def_epa",
    "form_plays": "home_plays"
})
away_form = form.rename(columns={
    "team": "away_team",
    "form_off_epa": "away_off_epa",
    "form_def_epa": "away_def_epa",
    "form_plays": "away_plays"
})

games = pd.merge(games, home_form, on=["game_id", "home_team"], how="left")
games = pd.merge(games, away_form, on=["game_id", "away_team"], how="left")

# Now fill the gaps for upcoming games using current form.
cur_home = current_form.rename(columns={
    "team": "home_team",
    "form_off_epa": "cur_home_off",
    "form_def_epa": "cur_home_def",
    "form_plays": "cur_home_plays"
})
cur_away = current_form.rename(columns={
    "team": "away_team",
    "form_off_epa": "cur_away_off",
    "form_def_epa": "cur_away_def",
    "form_plays": "cur_away_plays"
})

games = pd.merge(games, cur_home[["home_team", "cur_home_off", "cur_home_def", "cur_home_plays"]],
                 on="home_team", how="left")
games = pd.merge(games, cur_away[["away_team", "cur_away_off", "cur_away_def", "cur_away_plays"]],
                 on="away_team", how="left")

games["home_off_epa"] = games["home_off_epa"].fillna(games["cur_home_off"])
games["home_def_epa"] = games["home_def_epa"].fillna(games["cur_home_def"])
games["home_plays"] = games["home_plays"].fillna(games["cur_home_plays"])
games["away_off_epa"] = games["away_off_epa"].fillna(games["cur_away_off"])
games["away_def_epa"] = games["away_def_epa"].fillna(games["cur_away_def"])
games["away_plays"] = games["away_plays"].fillna(games["cur_away_plays"])

# The four features, all as home minus away.
games["off_epa_diff"] = games["home_off_epa"] - games["away_off_epa"]
games["def_epa_diff"] = games["home_def_epa"] - games["away_def_epa"]
games["pace_diff"] = games["home_plays"] - games["away_plays"]
games["rest_diff"] = games["home_rest"] - games["away_rest"]

# The thing I'm predicting. result is home score minus away score, so a
# positive result means the home team won.
games["home_won"] = np.where(games["result"] > 0, 1, 0)

feature_names = ["off_epa_diff", "def_epa_diff", "pace_diff", "rest_diff", "div_game"]

# Drop anything missing a feature - mostly the first few games of 2016, before
# any team had built up enough history.
before = len(games)
games = games.dropna(subset=feature_names).reset_index(drop=True)
print("Dropped " + str(before - len(games)) + " games with not enough history")
print("Games ready to use: " + str(len(games)))

# Ties are rare but real, and they're not a home win or a home loss. I drop
# them rather than pretend they're one or the other.
ties = games[games["is_played"] & (games["result"] == 0)]
print("Dropping " + str(len(ties)) + " tie games")
games = games[~(games["is_played"] & (games["result"] == 0))].reset_index(drop=True)


# ---------------------------------------------------------------------------
# Part 6: train the model
# ---------------------------------------------------------------------------
# Logistic regression. In plain terms: it draws one straight line through the
# feature space and asks which side of it a game falls on, then converts the
# distance from that line into a probability between 0 and 1. It's the simplest
# thing that gives me a real probability instead of just a yes/no, and because
# each feature gets one coefficient I can actually explain what it learned.
#
# I split by season, not randomly. A random split would let the model train on
# December 2025 and get tested on September 2025, which is a form of time
# travel. Training on the past and testing on the future is the only split that
# tells me what I'd actually get in practice.

print("")
print("Training the model...")

from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, roc_auc_score, log_loss

played = games[games["is_played"]].copy()

train = played[played["season"] <= TRAIN_THROUGH]
test = played[played["season"] > TRAIN_THROUGH]

X_train = train[feature_names]
y_train = train["home_won"]
X_test = test[feature_names]
y_test = test["home_won"]

print("Training games: " + str(len(train)) + " (seasons " + str(train["season"].min()) + "-" + str(TRAIN_THROUGH) + ")")
print("Testing games:  " + str(len(test)) + " (seasons " + str(test["season"].min()) + "-" + str(test["season"].max()) + ")")

# The features are on wildly different scales - EPA is around 0.1, pace is
# around 65. Without scaling, the model would treat a one-play pace difference
# as far more important than a huge EPA gap. I fit the scaler on training data
# only, so the test set stays genuinely unseen.
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

model = LogisticRegression(max_iter=1000)
model.fit(X_train_scaled, y_train)

test_probs = model.predict_proba(X_test_scaled)[:, 1]
test_preds = model.predict(X_test_scaled)

accuracy = accuracy_score(y_test, test_preds)
auc = roc_auc_score(y_test, test_probs)
loss = log_loss(y_test, test_probs)

# The number to beat. If I just picked the home team every single time, this is
# what I'd get. A model that can't clear this isn't doing anything.
baseline = y_test.mean()

print("")
print("--- How it did on games it never saw ---")
print("Accuracy:      " + str(round(accuracy, 4)))
print("Always-home:   " + str(round(baseline, 4)) + "   <- the number to beat")
print("ROC AUC:       " + str(round(auc, 4)) + "   (0.5 is a coin flip, 1.0 is perfect)")
print("Log loss:      " + str(round(loss, 4)) + "   (punishes confident wrong answers, lower is better)")

print("")
print("--- What the model learned ---")
print("Positive means it pushes the prediction toward the home team.")
coefs = pd.DataFrame({
    "feature": feature_names,
    "coefficient": model.coef_[0]
})
coefs = coefs.sort_values("coefficient", ascending=False)
print(coefs.to_string(index=False))


# ---------------------------------------------------------------------------
# Part 7: predict every game and save
# ---------------------------------------------------------------------------

print("")
print("Predicting every game...")

X_all = scaler.transform(games[feature_names])
games["home_win_prob"] = model.predict_proba(X_all)[:, 1]

# Turn the probability into a pick. Whoever is over 50% is the pick, and the
# confidence is how far from a coin flip it is.
games["predicted_winner"] = np.where(
    games["home_win_prob"] >= 0.5, games["home_team"], games["away_team"]
)
games["confidence"] = np.where(
    games["home_win_prob"] >= 0.5, games["home_win_prob"], 1 - games["home_win_prob"]
)

games["actual_winner"] = np.where(
    games["is_played"], np.where(games["result"] > 0, games["home_team"], games["away_team"]), None
)
games["was_correct"] = np.where(
    games["is_played"], games["predicted_winner"] == games["actual_winner"], None
)

os.makedirs(DATA_DIR, exist_ok=True)

out_cols = ["game_id", "season", "week", "gameday", "away_team", "home_team",
            "away_score", "home_score", "result", "spread_line", "div_game",
            "is_played", "home_win_prob", "predicted_winner", "confidence",
            "actual_winner", "was_correct",
            "home_off_epa", "home_def_epa", "home_plays",
            "away_off_epa", "away_def_epa", "away_plays",
            "off_epa_diff", "def_epa_diff", "pace_diff", "rest_diff"]

games[out_cols].to_csv(os.path.join(DATA_DIR, "predictions.csv"), index=False)
current_form.to_csv(os.path.join(DATA_DIR, "current_form.csv"), index=False)

# Team names, conference and division, so the app can show "Minnesota Vikings"
# instead of "MIN" and group the standings properly. I save it here rather than
# downloading it in the app, so the app never needs the internet.
teams = nfl.load_teams().to_pandas()
teams = teams[["team_abbr", "team_name", "team_nick", "team_conf",
               "team_division", "team_color", "team_logo_espn"]]
teams = teams[teams["team_abbr"].isin(games["home_team"].unique())]
teams.to_csv(os.path.join(DATA_DIR, "teams.csv"), index=False)

# The season-long form history, so the app can chart how a team trended.
team_form_history = team_games[["game_id", "season", "week", "gameday", "team",
                                "off_epa", "def_epa", "plays",
                                "form_off_epa", "form_def_epa", "form_plays"]]
team_form_history.to_csv(os.path.join(DATA_DIR, "team_form.csv"), index=False)

model_info = {
    "built_on": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
    "train_seasons": str(int(train["season"].min())) + "-" + str(TRAIN_THROUGH),
    "test_seasons": str(int(test["season"].min())) + "-" + str(int(test["season"].max())),
    "train_games": int(len(train)),
    "test_games": int(len(test)),
    "accuracy": float(accuracy),
    "baseline": float(baseline),
    "roc_auc": float(auc),
    "log_loss": float(loss),
    "form_through": str(current_form["form_through"].max().date()),
    "upcoming_season": int(LAST_SEASON),
    "form_window": FORM_WINDOW,
    "coefficients": dict(zip(feature_names, model.coef_[0].round(4).tolist()))
}

info_file = open(os.path.join(DATA_DIR, "model_info.json"), "w")
json.dump(model_info, info_file, indent=2)
info_file.close()

print("")
print("=" * 60)
print("Done. Saved to the data folder:")
print("  predictions.csv   - every game, predicted and actual")
print("  current_form.csv  - where each team stands right now")
print("  team_form.csv     - form game by game, for the charts")
print("  teams.csv         - team names, divisions, logos")
print("  model_info.json   - accuracy and coefficients")
print("")
print("Now run:  streamlit run app.py")
print("=" * 60)
