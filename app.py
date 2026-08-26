# app.py
#
# The Streamlit front end for my NFL game predictor.
#
# All this file does is read the CSVs that build_data.py already made and put
# them on screen. No modeling happens here - I wanted the app to open instantly
# instead of retraining every time somebody clicks something.
#
# Usage:  streamlit run app.py

import os
import json
import pandas as pd
import streamlit as st

# These two are only here for the charts further down. I let Streamlit draw the
# tables itself, but I build the actual plots with seaborn so I can control the
# axes - Streamlit's built-in charts auto-scaled the EPA lines so badly that the
# data ended up squashed into one corner of the plot.
import matplotlib.pyplot as plt
import seaborn as sns

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")

# My two chart colors. I checked these are still tellable apart with the common
# kinds of colorblindness, so the charts work for everybody.
BLUE = "#1F6FD0"
ORANGE = "#C96A22"
GRID = "#DDDDD8"
INK = "#3A3A38"
MUTED = "#77776F"

sns.set_style("white")


st.set_page_config(page_title="NFL Game Predictor", page_icon="football",
                   layout="wide")


# ---------------------------------------------------------------------------
# Loading the data
# ---------------------------------------------------------------------------
# The cache decorator means Streamlit reads these files once and then keeps
# them in memory. Without it, every single click would re-read the CSVs.

@st.cache_data
def load_everything():
    predictions = pd.read_csv(os.path.join(DATA_DIR, "predictions.csv"))
    predictions["gameday"] = pd.to_datetime(predictions["gameday"])

    teams = pd.read_csv(os.path.join(DATA_DIR, "teams.csv"))
    form_history = pd.read_csv(os.path.join(DATA_DIR, "team_form.csv"))
    current_form = pd.read_csv(os.path.join(DATA_DIR, "current_form.csv"))

    info_file = open(os.path.join(DATA_DIR, "model_info.json"))
    info = json.load(info_file)
    info_file.close()

    return predictions, teams, form_history, current_form, info


if not os.path.exists(os.path.join(DATA_DIR, "predictions.csv")):
    st.error("I can't find the data files yet.")
    st.write("Run this first, then reload the page:")
    st.code("python build_data.py")
    st.stop()

predictions, teams, form_history, current_form, info = load_everything()

UPCOMING_SEASON = info["upcoming_season"]

# A lookup so I can turn "MIN" into "Minnesota Vikings" anywhere I want.
name_lookup = dict(zip(teams["team_abbr"], teams["team_name"]))
logo_lookup = dict(zip(teams["team_abbr"], teams["team_logo_espn"]))


def full_name(abbr):
    # Falls back to the abbreviation if a team is somehow missing, so the app
    # never crashes just because of a name lookup.
    return name_lookup.get(abbr, abbr)


def as_percent(number):
    return str(int(round(number * 100))) + "%"


def tidy_axes(ax):
    # Every chart in here gets the same treatment: drop the box around the plot,
    # keep only a faint horizontal grid, and push the axis text back so the data
    # is the loudest thing on screen.
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.yaxis.grid(True, color=GRID, linewidth=0.8)
    ax.xaxis.grid(False)
    ax.set_axisbelow(True)
    ax.tick_params(colors=MUTED, length=0, labelsize=9)


# ---------------------------------------------------------------------------
# The sidebar - this is where you pick your team
# ---------------------------------------------------------------------------

st.sidebar.title("Pick a team")

# I sort by the full name so the dropdown reads alphabetically the way a person
# would expect - Arizona at the top, Washington at the bottom.
teams_sorted = teams.sort_values("team_name")
team_choices = list(teams_sorted["team_abbr"])

selected_team = st.sidebar.selectbox(
    "Team",
    team_choices,
    format_func=full_name,
    index=team_choices.index("MIN") if "MIN" in team_choices else 0
)

st.sidebar.image(logo_lookup.get(selected_team, ""), width=110)

team_row = teams[teams["team_abbr"] == selected_team].iloc[0]
st.sidebar.write("**" + team_row["team_division"] + "**")

st.sidebar.divider()
st.sidebar.caption(
    "The model is a logistic regression trained on "
    + info["train_seasons"] + " and tested on " + info["test_seasons"] + "."
)
st.sidebar.caption("Data rebuilt " + info["built_on"] + ".")
st.sidebar.caption("Team form is current through " + info["form_through"] + ".")


# ---------------------------------------------------------------------------
# The header - how good is this model, honestly
# ---------------------------------------------------------------------------
# I put the accuracy right at the top on purpose. A prediction app that hides
# its track record isn't worth much, and the honest number here is decent but
# not magic, so I'd rather lead with it than bury it.

st.title("NFL Game Predictor")
st.caption(
    "Predicts straight-up winners from each team's recent efficiency. "
    "Built on nflverse play-by-play data."
)

edge = round((info["accuracy"] - info["baseline"]) * 100, 1)

col1, col2, col3, col4 = st.columns(4)
col1.metric(
    "Accuracy on unseen games",
    as_percent(info["accuracy"]),
    delta="+" + str(edge) + " pts vs just picking home"
)
col2.metric("Just picking home every time", as_percent(info["baseline"]))
col3.metric("ROC AUC", str(round(info["roc_auc"], 3)))
col4.metric("Games tested", str(info["test_games"]))

st.divider()


# ---------------------------------------------------------------------------
# Some small helpers I use in both tabs
# ---------------------------------------------------------------------------

def games_for_team(frame, team):
    # Every game where this team is either the home side or the away side.
    is_home = frame["home_team"] == team
    is_away = frame["away_team"] == team
    return frame[is_home | is_away].copy()


def add_team_view(frame, team):
    # The raw table is written from the home team's point of view. This flips
    # it around so it reads from the selected team's point of view instead -
    # who they play, whether it's home or away, and their own win chance.
    frame = frame.copy()
    frame["is_home"] = frame["home_team"] == team
    frame["opponent"] = frame["away_team"].where(frame["is_home"], frame["home_team"])
    frame["site"] = frame["is_home"].map({True: "vs", False: "at"})
    frame["team_win_prob"] = frame["home_win_prob"].where(
        frame["is_home"], 1 - frame["home_win_prob"]
    )
    return frame


def expected_wins_table(frame):
    # The right way to project a record from a model that outputs probabilities
    # is to add the probabilities up, not to count how many games it picked you
    # to win. If I counted picks, a team the model likes even slightly would go
    # 17-0, which is obviously not what the model actually believes. Adding the
    # probabilities says "about 12 wins", which is what it really means.
    home_side = frame.groupby("home_team")["home_win_prob"].sum()
    away_side = frame.groupby("away_team")["home_win_prob"].apply(lambda s: (1 - s).sum())

    home_games = frame.groupby("home_team").size()
    away_games = frame.groupby("away_team").size()

    wins = home_side.add(away_side, fill_value=0)
    played = home_games.add(away_games, fill_value=0)

    table = pd.DataFrame({"proj_wins": wins, "games": played})
    # Adding two series that were grouped on different column names leaves the
    # index without a reliable name, so I set it myself before resetting it.
    table.index.name = "team_abbr"
    table = table.reset_index()
    table["proj_losses"] = table["games"] - table["proj_wins"]
    table["proj_wins"] = table["proj_wins"].round(1)
    table["proj_losses"] = table["proj_losses"].round(1)
    return table


upcoming = predictions[
    (predictions["season"] == UPCOMING_SEASON) & (~predictions["is_played"])
].copy()

history = predictions[predictions["is_played"]].copy()


# ---------------------------------------------------------------------------
# The two tabs
# ---------------------------------------------------------------------------

tab_upcoming, tab_record = st.tabs(
    ["Upcoming - " + str(UPCOMING_SEASON) + " season", "Track record - " + info["test_seasons"]]
)


# ===========================================================================
# TAB 1 - what the model thinks about games that haven't happened
# ===========================================================================

with tab_upcoming:

    if len(upcoming) == 0:
        st.info("There are no upcoming games in the data right now.")
    else:
        st.subheader(full_name(selected_team) + " - " + str(UPCOMING_SEASON) + " projections")

        standings = expected_wins_table(upcoming)
        standings = pd.merge(
            standings, teams, left_on="team_abbr", right_on="team_abbr", how="left"
        )
        standings = standings.sort_values("proj_wins", ascending=False).reset_index(drop=True)
        standings["rank"] = standings.index + 1

        my_row = standings[standings["team_abbr"] == selected_team].iloc[0]
        my_form = current_form[current_form["team"] == selected_team].iloc[0]

        # Ranks for the form stats, so the numbers mean something. EPA on
        # offense is better when it's higher; on defense it's better when it's
        # lower, so that one gets sorted the other way.
        off_rank = current_form["form_off_epa"].rank(ascending=False)
        def_rank = current_form["form_def_epa"].rank(ascending=True)
        current_form_ranked = current_form.copy()
        current_form_ranked["off_rank"] = off_rank
        current_form_ranked["def_rank"] = def_rank
        my_ranks = current_form_ranked[current_form_ranked["team"] == selected_team].iloc[0]

        a, b, c, d = st.columns(4)
        a.metric(
            "Projected record",
            str(my_row["proj_wins"]) + " - " + str(my_row["proj_losses"])
        )
        b.metric("League rank", "#" + str(my_row["rank"]) + " of 32")
        c.metric(
            "Offense (EPA/play)",
            str(round(my_form["form_off_epa"], 3)),
            delta="#" + str(int(my_ranks["off_rank"])) + " in the league",
            delta_color="off"
        )
        d.metric(
            "Defense (EPA/play allowed)",
            str(round(my_form["form_def_epa"], 3)),
            delta="#" + str(int(my_ranks["def_rank"])) + " in the league",
            delta_color="off"
        )

        st.caption(
            "Projected record adds up the model's win probability for all "
            + str(int(my_row["games"])) + " games, which is why it isn't a whole number. "
            "Every team's form is frozen at " + info["form_through"]
            + " until real " + str(UPCOMING_SEASON) + " results come in - "
            "re-run build_data.py during the season and these update themselves."
        )

        st.divider()

        # --- the schedule, game by game ---
        st.markdown("#### Game by game")

        my_games = add_team_view(games_for_team(upcoming, selected_team), selected_team)
        my_games = my_games.sort_values("week")

        schedule_view = pd.DataFrame({
            "Week": my_games["week"],
            "Date": my_games["gameday"].dt.strftime("%b %d"),
            "Opponent": my_games["site"] + " " + my_games["opponent"].map(full_name),
            "Pick": my_games["predicted_winner"].map(full_name),
            "Win chance": my_games["team_win_prob"],
            "Vegas spread": pd.to_numeric(my_games["spread_line"], errors="coerce")
        })

        # A team plays 17 games across 18 weeks, so exactly one week is their
        # bye. Rather than leave a confusing gap in the week numbers, I work out
        # which week is missing and say so underneath.
        all_weeks = set(upcoming["week"].unique())
        played_weeks = set(my_games["week"])
        bye_weeks = sorted(all_weeks - played_weeks)

        st.dataframe(
            schedule_view,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Win chance": st.column_config.ProgressColumn(
                    "Win chance",
                    help="How likely the model thinks " + selected_team + " is to win",
                    format="percent",
                    min_value=0.0,
                    max_value=1.0
                ),
                "Vegas spread": st.column_config.NumberColumn(
                    help="From the home team's side. Negative means the home team is the underdog. Blank means no line posted yet.",
                    format="%.1f"
                )
            }
        )

        if len(bye_weeks) > 0:
            st.caption("Bye week: Week " + str(bye_weeks[0]) + ".")

        st.divider()

        # --- the whole league ---
        st.markdown("#### Projected standings")
        st.caption("Click any column header to sort.")

        conference_pick = st.radio(
            "Show",
            ["Both conferences", "AFC", "NFC"],
            horizontal=True,
            label_visibility="collapsed"
        )

        shown = standings
        if conference_pick != "Both conferences":
            shown = standings[standings["team_conf"] == conference_pick]

        standings_view = pd.DataFrame({
            "Rank": shown["rank"],
            "Team": shown["team_name"],
            "Division": shown["team_division"],
            "Proj W": shown["proj_wins"],
            "Proj L": shown["proj_losses"]
        })

        st.dataframe(standings_view, hide_index=True, use_container_width=True, height=560)

        st.divider()

        # --- browse by week instead of by team ---
        st.markdown("#### Or look at a single week")

        week_pick = st.selectbox(
            "Week",
            sorted(upcoming["week"].unique()),
            format_func=lambda w: "Week " + str(w)
        )

        week_games = upcoming[upcoming["week"] == week_pick].sort_values("gameday")

        week_view = pd.DataFrame({
            "Date": week_games["gameday"].dt.strftime("%a %b %d"),
            "Away": week_games["away_team"].map(full_name),
            "Home": week_games["home_team"].map(full_name),
            "Pick": week_games["predicted_winner"].map(full_name),
            "Confidence": week_games["confidence"]
        })

        st.dataframe(
            week_view,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Confidence": st.column_config.ProgressColumn(
                    "Confidence", format="percent", min_value=0.0, max_value=1.0
                )
            }
        )


# ===========================================================================
# TAB 2 - how the model actually did on games it had never seen
# ===========================================================================

with tab_record:

    test_seasons = sorted(
        history[history["season"] > int(info["train_seasons"].split("-")[1])]["season"].unique()
    )
    scored = history[history["season"].isin(test_seasons)].copy()

    st.subheader("How the model did on games it never trained on")

    season_pick = st.radio(
        "Season",
        ["All"] + [str(int(s)) for s in test_seasons],
        horizontal=True
    )

    if season_pick != "All":
        scored = scored[scored["season"] == int(season_pick)]

    right = scored["was_correct"].sum()
    total = len(scored)

    e, f, g = st.columns(3)
    e.metric("Games predicted", str(total))
    e.caption("")
    f.metric("Got right", str(int(right)))
    g.metric("Accuracy", as_percent(right / total))

    st.divider()

    # --- does confidence actually mean anything ---
    # This is the check I care about most. A model can be 63% accurate overall
    # and still be useless if it's just as wrong when it's confident as when
    # it's guessing. If the bars go up left to right, the confidence number is
    # telling the truth and I can trust the strong picks more than the coin
    # flips.
    st.markdown("#### Is the model's confidence honest?")

    buckets = pd.cut(
        scored["confidence"],
        bins=[0.5, 0.55, 0.6, 0.65, 0.7, 1.0],
        labels=["50-55%", "55-60%", "60-65%", "65-70%", "70%+"],
        include_lowest=True
    )
    scored["bucket"] = buckets

    by_bucket = scored.groupby("bucket", observed=True).agg(
        games=("was_correct", "size"),
        accuracy=("was_correct", "mean")
    ).reset_index()

    bucket_left, bucket_right = st.columns([2, 1])

    with bucket_left:
        fig, ax = plt.subplots(figsize=(7, 3.6))

        bars = ax.bar(
            by_bucket["bucket"].astype(str),
            by_bucket["accuracy"],
            color=BLUE,
            width=0.62
        )

        # The coin-flip line. Any bar below this is a group of games where the
        # model would have been better off guessing.
        ax.axhline(0.5, color=ORANGE, linewidth=1.5, linestyle="--", zorder=3)
        # I park this label out past the last bar so it can't collide with the
        # percentage sitting on top of the first one.
        ax.set_xlim(-0.6, len(by_bucket) - 0.1)
        ax.text(
            len(by_bucket) - 0.5, 0.525, "coin flip",
            color=ORANGE, fontsize=9, va="bottom", ha="left"
        )

        # Writing the number on top of each bar means nobody has to read values
        # off the axis.
        for bar, value in zip(bars, by_bucket["accuracy"]):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                value + 0.015,
                as_percent(value),
                ha="center", va="bottom", fontsize=10, color=INK
            )

        ax.set_ylim(0, max(by_bucket["accuracy"]) + 0.12)
        ax.set_ylabel("Accuracy", color=MUTED, fontsize=9)
        ax.set_xlabel("How confident the model was", color=MUTED, fontsize=9)
        ax.set_yticks([0, 0.25, 0.5, 0.75])
        ax.set_yticklabels(["0%", "25%", "50%", "75%"])
        tidy_axes(ax)

        fig.tight_layout()
        st.pyplot(fig, use_container_width=True)
        plt.close(fig)

    with bucket_right:
        bucket_view = pd.DataFrame({
            "How confident": by_bucket["bucket"],
            "Games": by_bucket["games"],
            "Accuracy": by_bucket["accuracy"].map(as_percent)
        })
        st.dataframe(bucket_view, hide_index=True, use_container_width=True)

    st.caption(
        "If the bars climb left to right, the confidence number is meaningful - "
        "the games the model felt strongly about really did go its way more often."
    )

    st.divider()

    # --- the selected team's actual results ---
    st.markdown("#### " + full_name(selected_team) + " - every prediction and what happened")

    team_scored = add_team_view(games_for_team(scored, selected_team), selected_team)
    team_scored = team_scored.sort_values(["season", "week"])

    if len(team_scored) == 0:
        st.info("No games for this team in the seasons selected.")
    else:
        team_right = team_scored["was_correct"].sum()
        st.write(
            "The model got **" + str(int(team_right)) + " of "
            + str(len(team_scored)) + "** "
            + full_name(selected_team) + " games right ("
            + as_percent(team_right / len(team_scored)) + ")."
        )

        # The raw score columns are away-then-home, which is confusing when
        # you're looking at one team. I flip it so it always reads as the
        # selected team's score first, with a W or an L in front of it.
        team_points = team_scored["home_score"].where(
            team_scored["is_home"], team_scored["away_score"]
        )
        opp_points = team_scored["away_score"].where(
            team_scored["is_home"], team_scored["home_score"]
        )
        won_it = team_scored["actual_winner"] == selected_team

        score_text = (
            won_it.map({True: "W ", False: "L "})
            + team_points.astype(int).astype(str)
            + "-"
            + opp_points.astype(int).astype(str)
        )

        results_view = pd.DataFrame({
            "Season": team_scored["season"],
            "Week": team_scored["week"],
            "Opponent": team_scored["site"] + " " + team_scored["opponent"].map(full_name),
            "Result": score_text,
            "Model picked": team_scored["predicted_winner"].map(full_name),
            "Right?": team_scored["was_correct"].map({True: "Correct", False: "Wrong"})
        })

        st.dataframe(results_view, hide_index=True, use_container_width=True, height=420)

    st.divider()

    # --- how this team's form moved over a season ---
    # These are the two numbers that actually drive the model, so seeing them
    # move is seeing the model change its mind.
    st.markdown("#### " + full_name(selected_team) + " - form over the season")

    form_seasons = sorted(form_history["season"].unique())
    form_season_pick = st.selectbox(
        "Season to chart",
        form_seasons,
        index=len(form_seasons) - 1,
        format_func=lambda s: str(int(s))
    )

    team_form = form_history[
        (form_history["team"] == selected_team)
        & (form_history["season"] == form_season_pick)
    ].sort_values("week")

    if len(team_form) == 0:
        st.info("No form data for that team and season.")
    else:
        fig, ax = plt.subplots(figsize=(9, 3.8))

        weeks = team_form["week"]
        off_line = team_form["form_off_epa"]
        def_line = team_form["form_def_epa"]

        # Zero is the reference that makes these numbers mean anything - it's a
        # league-average play. Above the line on offense is good, below it on
        # defense is good.
        ax.axhline(0, color=GRID, linewidth=1.2, zorder=1)

        ax.plot(weeks, off_line, color=ORANGE, linewidth=2,
                marker="o", markersize=5, label="Offense", zorder=3)
        ax.plot(weeks, def_line, color=BLUE, linewidth=2,
                marker="o", markersize=5, label="Defense allowed", zorder=3)

        # Labelling the lines directly means the reader never has to look away
        # to a legend box to work out which line is which.
        last_week = weeks.iloc[-1]
        ax.text(last_week + 0.25, off_line.iloc[-1], "Offense",
                color=ORANGE, fontsize=10, va="center")
        ax.text(last_week + 0.25, def_line.iloc[-1], "Defense allowed",
                color=BLUE, fontsize=10, va="center")

        # A little headroom on the right so those labels aren't clipped, and
        # padding on y so the lines don't sit flat against the frame.
        span = max(off_line.max(), def_line.max()) - min(off_line.min(), def_line.min())
        pad = max(span * 0.25, 0.03)
        ax.set_xlim(weeks.min() - 0.5, last_week + 4.5)
        ax.set_ylim(min(off_line.min(), def_line.min()) - pad,
                    max(off_line.max(), def_line.max()) + pad)

        ax.set_xlabel("Week", color=MUTED, fontsize=9)
        ax.set_ylabel("EPA per play", color=MUTED, fontsize=9)
        ax.set_xticks(list(weeks))
        tidy_axes(ax)

        fig.tight_layout()
        st.pyplot(fig, use_container_width=True)
        plt.close(fig)

        st.caption(
            "Both lines are rolling averages of the previous "
            + str(info["form_window"]) + " games, which is exactly what the model sees. "
            "Offense is better when it's higher. Defense is better when it's LOWER - "
            "it's points the other team gained, so down is good."
        )


# ---------------------------------------------------------------------------
# Footer - the honest caveats
# ---------------------------------------------------------------------------

st.divider()

with st.expander("How this works, and what it can't do"):
    st.markdown(
        "**The model.** Logistic regression, trained on "
        + str(info["train_games"]) + " games from " + info["train_seasons"]
        + " and tested on " + str(info["test_games"]) + " games from "
        + info["test_seasons"] + " that it never saw during training. "
        "It looks at five things, all written as the home team's number minus "
        "the away team's: recent offensive efficiency, recent defensive "
        "efficiency, pace, rest days, and whether it's a division game."
    )
    st.markdown(
        "**What it learned.** These are the coefficients. Positive means the "
        "feature pushes the prediction toward the home team."
    )
    coef_frame = pd.DataFrame(
        list(info["coefficients"].items()), columns=["Feature", "Coefficient"]
    ).sort_values("Coefficient", ascending=False)
    st.dataframe(coef_frame, hide_index=True, use_container_width=True)
    st.markdown(
        "Offensive efficiency dominates and defense is second, which is what "
        "you'd hope - the model landed on football logic on its own rather "
        "than on something weird."
    )
    st.markdown(
        "**What it can't do.** It doesn't know about injuries, so a team that "
        "just lost its quarterback still looks as good as it did last week. It "
        "has no idea about weather, coaching changes, or anything that happened "
        "in the offseason. And it does not beat the betting spread - I tested "
        "that separately and the market has this data priced in already. This "
        "predicts who wins, not who covers."
    )
