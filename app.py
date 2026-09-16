"""Streamlit dashboard for the generated NFL prediction artifacts."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st


ROOT = Path(__file__).resolve().parent
DATA_DIRECTORY = ROOT / "data"
sys.path.insert(0, str(ROOT / "python"))

from nfl_predictor.dashboard import (  # noqa: E402
    add_form_ranks,
    add_team_view,
    evaluation_games,
    games_for_team,
    load_dashboard_data,
    projected_standings,
)
from nfl_predictor.validation import DataValidationError  # noqa: E402


st.set_page_config(
    page_title="NFL Game Predictor",
    page_icon="🏈",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data(show_spinner=False)
def load_data():
    return load_dashboard_data(DATA_DIRECTORY)


try:
    data = load_data()
except (DataValidationError, FileNotFoundError, OSError, ValueError) as exc:
    st.error("The generated prediction data could not be loaded.")
    st.code(str(exc))
    st.info("From the repository root, run: python python/build_data.py")
    st.stop()


predictions = data.predictions
teams = data.teams
form_history = data.form_history
current_form = add_form_ranks(data.current_form)
info = data.model_info
season = int(info["upcoming_season"])

team_names = dict(zip(teams["team_abbr"], teams["team_name"]))
team_logos = dict(zip(teams["team_abbr"], teams["team_logo_espn"]))


def full_name(team: str) -> str:
    return team_names.get(team, team)


def percent(value: float, digits: int = 0) -> str:
    return f"{value:.{digits}%}"


def score_for_team(row: pd.Series, team: str) -> str:
    if not row["is_played"]:
        return "Upcoming"
    team_score = row["home_score"] if row["is_home"] else row["away_score"]
    opponent_score = row["away_score"] if row["is_home"] else row["home_score"]
    if pd.isna(team_score) or pd.isna(opponent_score):
        return "Final"
    if row["actual_winner"] == team:
        outcome = "W"
    elif row["actual_winner"] == row["opponent"]:
        outcome = "L"
    else:
        outcome = "T"
    return f"{outcome} {int(team_score)}-{int(opponent_score)}"


teams_sorted = teams.sort_values("team_name")
team_choices = teams_sorted["team_abbr"].tolist()
default_index = team_choices.index("MIN") if "MIN" in team_choices else 0

st.sidebar.title("🏈 Team dashboard")
selected_team = st.sidebar.selectbox(
    "NFL team", team_choices, index=default_index, format_func=full_name
)
selected_metadata = teams[teams["team_abbr"] == selected_team].iloc[0]
logo = team_logos.get(selected_team)
if isinstance(logo, str) and logo:
    st.sidebar.image(logo, width=112)
st.sidebar.markdown(f"**{selected_metadata['team_division']}**")
st.sidebar.divider()
st.sidebar.caption(f"Model trained on {info['train_seasons']}")
st.sidebar.caption(f"Held-out evaluation: {info['test_seasons']}")
st.sidebar.caption(f"Team form through {info['form_through']}")
st.sidebar.caption(f"Artifacts built {info['built_on']}")

st.title("🏈 NFL Game Predictor")
st.caption(
    "Explainable win probabilities from recent efficiency and pregame Elo, "
    "built with Python, scikit-learn, and nflverse data."
)

edge = info["accuracy"] - info["baseline"]
metric_columns = st.columns(4)
metric_columns[0].metric(
    "Held-out accuracy", percent(info["accuracy"], 1), f"+{edge:.1%} vs baseline"
)
metric_columns[1].metric("Home-team baseline", percent(info["baseline"], 1))
metric_columns[2].metric("ROC AUC", f"{info['roc_auc']:.3f}")
metric_columns[3].metric("Games tested", f"{info['test_games']:,}")

season_games = predictions[predictions["season"] == season].copy()
standings = projected_standings(predictions, teams, season)
selected_standing = standings[standings["team_abbr"] == selected_team].iloc[0]
selected_form = current_form[current_form["team"] == selected_team].iloc[0]

team_tab, league_tab, model_tab = st.tabs(
    [f"{full_name(selected_team)} outlook", "League predictions", "Model report"]
)

with team_tab:
    st.subheader(f"{full_name(selected_team)} · {season}")
    selected_schedule = add_team_view(
        games_for_team(season_games, selected_team), selected_team
    ).sort_values(["week", "gameday"])
    selected_elo = None
    if not selected_schedule.empty:
        next_games = selected_schedule[~selected_schedule["is_played"]]
        rating_row = (
            next_games.iloc[0] if not next_games.empty else selected_schedule.iloc[-1]
        )
        selected_elo = (
            rating_row["home_elo"] if rating_row["is_home"] else rating_row["away_elo"]
        )

    team_metrics = st.columns(5)
    team_metrics[0].metric(
        "Projected record",
        f"{selected_standing['projected_wins']:.1f}-{selected_standing['projected_losses']:.1f}",
    )
    team_metrics[1].metric("League rank", f"#{selected_standing['rank']} of 32")
    team_metrics[2].metric(
        "Offensive EPA/play",
        f"{selected_form['form_off_epa']:.3f}",
        f"#{selected_form['off_rank']} in NFL",
        delta_color="off",
    )
    team_metrics[3].metric(
        "Defensive EPA allowed",
        f"{selected_form['form_def_epa']:.3f}",
        f"#{selected_form['def_rank']} in NFL",
        delta_color="off",
    )
    team_metrics[4].metric(
        "Pregame Elo", "N/A" if selected_elo is None else f"{selected_elo:.0f}"
    )
    st.caption(
        f"Projection includes {selected_standing['actual_wins']} actual win(s) from "
        f"{selected_standing['completed_games']} completed game(s), plus expected wins "
        "from the remaining schedule. Decimal records are intentional."
    )

    if selected_schedule.empty:
        st.info("No schedule is available for this team and season.")
    else:
        schedule_view = pd.DataFrame(
            {
                "Week": selected_schedule["week"],
                "Date": selected_schedule["gameday"].dt.strftime("%b %d"),
                "Opponent": selected_schedule["site"]
                + " "
                + selected_schedule["opponent"].map(full_name),
                "Result": selected_schedule.apply(
                    score_for_team, axis=1, team=selected_team
                ),
                "Model pick": selected_schedule["predicted_winner"].map(full_name),
                "Win probability": selected_schedule["team_win_prob"],
                "Elo edge": selected_schedule["elo_diff"].where(
                    selected_schedule["is_home"], -selected_schedule["elo_diff"]
                ).round(),
            }
        )
        st.markdown("#### Full schedule")
        st.dataframe(
            schedule_view,
            hide_index=True,
            width="stretch",
            column_config={
                "Win probability": st.column_config.ProgressColumn(
                    "Win probability", format="percent", min_value=0, max_value=1
                )
            },
        )

with league_tab:
    st.subheader(f"{season} projected standings")
    conference = st.radio("Conference", ["All", "AFC", "NFC"], horizontal=True)
    shown_standings = standings
    if conference != "All":
        shown_standings = standings[standings["team_conf"] == conference]
    standings_view = pd.DataFrame(
        {
            "Rank": shown_standings["rank"],
            "Team": shown_standings["team_name"],
            "Division": shown_standings["team_division"],
            "Actual wins": shown_standings["actual_wins"],
            "Projected W": shown_standings["projected_wins"].round(1),
            "Projected L": shown_standings["projected_losses"].round(1),
        }
    )
    st.dataframe(standings_view, hide_index=True, width="stretch", height=560)

    future_games = season_games[~season_games["is_played"]]
    if future_games.empty:
        st.info("There are no unplayed games in the current data.")
    else:
        st.markdown("#### Browse upcoming games by week")
        week = st.selectbox("Week", sorted(future_games["week"].unique()))
        week_games = future_games[future_games["week"] == week].sort_values(
            ["gameday", "game_id"]
        )
        week_view = pd.DataFrame(
            {
                "Date": week_games["gameday"].dt.strftime("%a, %b %d"),
                "Away": week_games["away_team"].map(full_name),
                "Home": week_games["home_team"].map(full_name),
                "Pick": week_games["predicted_winner"].map(full_name),
                "Confidence": week_games["confidence"],
            }
        )
        st.dataframe(
            week_view,
            hide_index=True,
            width="stretch",
            column_config={
                "Confidence": st.column_config.ProgressColumn(
                    "Confidence", format="percent", min_value=0.5, max_value=1
                )
            },
        )

with model_tab:
    st.subheader("Performance on games the model never trained on")
    detail_metrics = st.columns(4)
    detail_metrics[0].metric("Accuracy", percent(info["accuracy"], 1))
    detail_metrics[1].metric("Log loss", f"{info['log_loss']:.3f}")
    detail_metrics[2].metric("ROC AUC", f"{info['roc_auc']:.3f}")
    detail_metrics[3].metric("Test sample", f"{info['test_games']:,} games")

    comparison = info["model_comparison"]
    accuracy_gain = comparison["accuracy_after"] - comparison["accuracy_before"]
    auc_gain = comparison["roc_auc_after"] - comparison["roc_auc_before"]
    st.success(
        "Adding pregame Elo improved held-out accuracy from "
        f"{percent(comparison['accuracy_before'], 1)} to "
        f"{percent(comparison['accuracy_after'], 1)} "
        f"(+{accuracy_gain:.1%}) and ROC AUC by {auc_gain:.3f}."
    )
    st.caption(comparison["parameter_selection"])

    confidence_frame = pd.DataFrame(info["confidence_buckets"]).rename(
        columns={
            "bucket": "Confidence",
            "games": "Games",
            "accuracy": "Accuracy",
            "average_confidence": "Average confidence",
        }
    )
    st.markdown("#### Confidence calibration")
    st.dataframe(
        confidence_frame,
        hide_index=True,
        width="stretch",
        column_config={
            "Accuracy": st.column_config.ProgressColumn(
                "Accuracy", format="percent", min_value=0, max_value=1
            ),
            "Average confidence": st.column_config.NumberColumn(
                "Average confidence", format="percent"
            ),
        },
    )

    report_left, report_right = st.columns(2)
    with report_left:
        st.markdown("#### Feature coefficients")
        coefficient_frame = pd.DataFrame(
            info["coefficients"].items(), columns=["Feature", "Coefficient"]
        ).sort_values("Coefficient", ascending=False)
        st.dataframe(coefficient_frame, hide_index=True, width="stretch")
        st.caption(
            "Positive values move a prediction toward the home team; negative "
            "values move it toward the away team."
        )
    with report_right:
        st.markdown("#### Confusion matrix")
        matrix = info["confusion_matrix"]
        matrix_frame = pd.DataFrame(
            [
                [matrix["true_negative"], matrix["false_positive"]],
                [matrix["false_negative"], matrix["true_positive"]],
            ],
            index=["Actual away winner", "Actual home winner"],
            columns=["Predicted away", "Predicted home"],
        )
        st.dataframe(matrix_frame, width="stretch")

    st.markdown(f"#### {full_name(selected_team)} held-out predictions")
    scored = evaluation_games(predictions, info["train_seasons"])
    team_scored = add_team_view(
        games_for_team(scored, selected_team), selected_team
    ).sort_values(["season", "week"])
    if team_scored.empty:
        st.info("No held-out games are available for this team.")
    else:
        team_results = pd.DataFrame(
            {
                "Season": team_scored["season"],
                "Week": team_scored["week"],
                "Opponent": team_scored["site"]
                + " "
                + team_scored["opponent"].map(full_name),
                "Result": team_scored.apply(
                    score_for_team, axis=1, team=selected_team
                ),
                "Pick": team_scored["predicted_winner"].map(full_name),
                "Model result": team_scored["was_correct"].map(
                    {True: "Correct", False: "Wrong"}
                ),
            }
        )
        st.dataframe(
            team_results, hide_index=True, width="stretch", height=360
        )

    available_form_seasons = sorted(form_history["season"].unique())
    form_season = st.selectbox(
        "Form history season",
        available_form_seasons,
        index=len(available_form_seasons) - 1,
        format_func=lambda value: str(int(value)),
    )
    team_form = form_history[
        (form_history["team"] == selected_team)
        & (form_history["season"] == form_season)
    ].sort_values("week")
    if not team_form.empty:
        chart = team_form.set_index("week")[["form_off_epa", "form_def_epa"]]
        chart = chart.rename(
            columns={
                "form_off_epa": "Offensive EPA/play",
                "form_def_epa": "Defensive EPA/play allowed",
            }
        )
        st.line_chart(chart)

    with st.expander("Methodology and limitations"):
        st.write(
            f"The logistic regression was trained on {info['train_games']:,} games "
            f"from {info['train_seasons']} and evaluated on {info['test_games']:,} "
            f"later games from {info['test_seasons']}. Rolling form is shifted by "
            "one game, Elo is recorded before each result updates the ratings, and "
            "preprocessing is fit on training data only."
        )
        st.write(
            f"Elo uses K={info['elo']['k_factor']:.0f}, carries "
            f"{info['elo']['season_carryover']:.0%} of rating differences into the "
            "next season, and uses a home-field adjustment only when updating ratings."
        )
        for limitation in info["limitations"]:
            st.markdown(f"- {limitation}")

st.divider()
st.caption(
    "Data: nflverse · Model: logistic regression · Predictions are for "
    "straight-up winners, not betting advice."
)
