const state = {
    teams: [],
    model: null,
    standings: [],
    upcoming: []
};

const featureLabels = {
    off_epa_diff: "Recent offensive EPA per play",
    def_epa_diff: "Recent defensive EPA allowed",
    pace_diff: "Recent offensive plays per game",
    rest_diff: "Rest days before kickoff",
    div_game: "Division matchup indicator"
};

const elements = {
    status: document.querySelector("#status"),
    predictions: document.querySelector("#predictions"),
    league: document.querySelector("#league-section"),
    modelSection: document.querySelector("#model"),
    teamSelect: document.querySelector("#team-select"),
    weekSelect: document.querySelector("#week-select"),
    conferenceSelect: document.querySelector("#conference-select")
};

async function fetchJson(path) {
    const response = await fetch(path);
    if (!response.ok) {
        let message = `Request failed (${response.status})`;
        try {
            const error = await response.json();
            message = error.message || message;
        } catch (_) {
            // A non-JSON error still gets the useful HTTP status above.
        }
        throw new Error(message);
    }
    return response.json();
}

function percent(value, digits = 0) {
    return `${(value * 100).toFixed(digits)}%`;
}

function shortDate(value) {
    return new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric" })
        .format(new Date(`${value}T12:00:00`));
}

function setText(selector, value) {
    document.querySelector(selector).textContent = value;
}

function clear(node) {
    node.replaceChildren();
}

function make(tag, text, className) {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    if (className) node.className = className;
    return node;
}

function teamName(abbreviation) {
    return state.teams.find(team => team.abbreviation === abbreviation)?.name || abbreviation;
}

function renderModel() {
    const info = state.model;
    const metrics = [
        [percent(info.accuracy, 1), "Accuracy on unseen games"],
        [percent(info.baseline, 1), "Always-home baseline"],
        [info.rocAuc.toFixed(3), "ROC AUC"],
        [info.testGames.toLocaleString(), "Games tested"]
    ];
    const container = document.querySelector("#model-metrics");
    clear(container);
    metrics.forEach(([value, label]) => {
        const item = make("div", undefined, "metric");
        item.append(make("span", value, "metric-value"), make("span", label, "metric-label"));
        container.append(item);
    });

    const features = document.querySelector("#feature-list");
    clear(features);
    info.features.forEach(feature => features.append(make("li", featureLabels[feature] || feature)));
    setText("#training-summary", `Trained on ${info.trainSeasons}; tested chronologically on ${info.testSeasons}. The scaler is fit only on training games.`);

    const buckets = document.querySelector("#confidence-buckets");
    clear(buckets);
    info.confidenceBuckets.forEach(bucket => {
        const row = make("div", undefined, "bucket-row");
        const track = make("div", undefined, "bucket-track");
        const fill = make("div", undefined, "bucket-fill");
        const accuracy = bucket.accuracy ?? 0;
        fill.style.width = `${accuracy * 100}%`;
        track.append(fill);
        row.append(make("span", bucket.bucket), track, make("strong", percent(accuracy)));
        buckets.append(row);
    });

    const limitations = document.querySelector("#limitations");
    clear(limitations);
    info.limitations.forEach(item => limitations.append(make("li", item)));
}

function populateControls() {
    state.teams.forEach(team => {
        const option = make("option", team.name);
        option.value = team.abbreviation;
        elements.teamSelect.append(option);
    });
    elements.teamSelect.value = state.teams.some(team => team.abbreviation === "MIN") ? "MIN" : state.teams[0].abbreviation;

    const weeks = [...new Set(state.upcoming.map(game => game.week))].sort((a, b) => a - b);
    weeks.forEach(week => {
        const option = make("option", `Week ${week}`);
        option.value = week;
        elements.weekSelect.append(option);
    });
}

function renderTeamMetrics(details) {
    const metrics = [
        [`${details.standing.projectedWins} – ${details.standing.projectedLosses}`, "Projected record"],
        [`#${details.standing.rank} of 32`, "League rank"],
        [details.form.offensiveEpa.toFixed(3), `Offensive EPA · #${details.form.offensiveRank}`],
        [details.form.defensiveEpa.toFixed(3), `Defensive EPA allowed · #${details.form.defensiveRank}`]
    ];
    const container = document.querySelector("#team-metrics");
    clear(container);
    metrics.forEach(([value, label]) => {
        const item = make("div", undefined, "team-stat");
        item.append(make("strong", value), make("span", label));
        container.append(item);
    });
}

function renderTeamSchedule(games, abbreviation) {
    const body = document.querySelector("#team-schedule");
    clear(body);
    games.sort((a, b) => a.week - b.week).forEach(game => {
        const isHome = game.homeTeam === abbreviation;
        const opponent = isHome ? game.awayTeam : game.homeTeam;
        const teamProbability = isHome ? game.homeWinProbability : 1 - game.homeWinProbability;
        const row = document.createElement("tr");
        const matchup = `${isHome ? "vs" : "at"} ${teamName(opponent)}`;
        const status = game.played
            ? `${game.actualWinner === abbreviation ? "Won" : "Lost"} ${isHome ? game.homeScore : game.awayScore}–${isHome ? game.awayScore : game.homeScore}`
            : "Upcoming";
        [game.week, shortDate(game.gameday), matchup, teamName(game.predictedWinner)]
            .forEach(value => row.append(make("td", value)));
        row.append(make("td", percent(teamProbability), "probability"));
        row.append(make("td", status, game.played ? (game.actualWinner === abbreviation ? "correct" : "wrong") : ""));
        body.append(row);
    });
}

async function loadTeam(abbreviation) {
    try {
        const season = state.model.upcomingSeason;
        const [details, games] = await Promise.all([
            fetchJson(`/api/teams/${abbreviation}`),
            fetchJson(`/api/teams/${abbreviation}/games?season=${season}`)
        ]);
        const logo = document.querySelector("#team-logo");
        logo.src = details.team.logoUrl;
        logo.alt = `${details.team.name} logo`;
        setText("#team-name", details.team.name);
        setText("#team-division", details.team.division);
        setText("#form-through", `Form through ${details.form.formThrough}`);
        renderTeamMetrics(details);
        renderTeamSchedule(games, abbreviation);
    } catch (error) {
        showError(error);
    }
}

function renderWeeklyPredictions() {
    const week = Number(elements.weekSelect.value);
    const games = state.upcoming.filter(game => game.week === week);
    const container = document.querySelector("#weekly-predictions");
    clear(container);
    games.forEach(game => {
        const row = make("article", undefined, "game-row");
        const matchup = make("div");
        matchup.append(
            make("div", `${teamName(game.awayTeam)} at ${teamName(game.homeTeam)}`, "matchup"),
            make("p", shortDate(game.gameday), "game-meta")
        );
        const pick = make("div", undefined, "pick");
        pick.append(make("strong", teamName(game.predictedWinner)), make("span", `${percent(game.confidence)} confidence`));
        row.append(matchup, pick);
        container.append(row);
    });
}

function renderStandings() {
    const conference = elements.conferenceSelect.value;
    const rows = state.standings.filter(row => !conference || row.conference === conference);
    const body = document.querySelector("#standings-body");
    clear(body);
    rows.forEach(standing => {
        const row = document.createElement("tr");
        row.append(make("td", standing.rank), make("td", standing.teamName),
            make("td", standing.division),
            make("td", `${standing.projectedWins} – ${standing.projectedLosses}`));
        body.append(row);
    });
}

function showError(error) {
    elements.status.textContent = `Could not load the dashboard: ${error.message}`;
    elements.status.classList.add("error");
}

async function initialize() {
    try {
        const [teams, model] = await Promise.all([fetchJson("/api/teams"), fetchJson("/api/model")]);
        state.teams = teams;
        state.model = model;
        [state.standings, state.upcoming] = await Promise.all([
            fetchJson("/api/standings"),
            fetchJson(`/api/predictions?season=${model.upcomingSeason}&played=false`)
        ]);
        renderModel();
        populateControls();
        renderWeeklyPredictions();
        renderStandings();
        await loadTeam(elements.teamSelect.value);
        elements.status.textContent = "";
        elements.predictions.hidden = false;
        elements.league.hidden = false;
        elements.modelSection.hidden = false;
    } catch (error) {
        showError(error);
    }
}

elements.teamSelect.addEventListener("change", event => loadTeam(event.target.value));
elements.weekSelect.addEventListener("change", renderWeeklyPredictions);
elements.conferenceSelect.addEventListener("change", renderStandings);

initialize();
