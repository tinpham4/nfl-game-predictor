package com.tinpham.nflpredictor.service;

import com.tinpham.nflpredictor.config.DataProperties;
import com.tinpham.nflpredictor.exception.DataContractException;
import com.tinpham.nflpredictor.model.ConfidenceBucket;
import com.tinpham.nflpredictor.model.ConfusionMatrix;
import com.tinpham.nflpredictor.model.ModelInfo;
import com.tinpham.nflpredictor.model.Prediction;
import com.tinpham.nflpredictor.model.Team;
import com.tinpham.nflpredictor.model.TeamForm;
import jakarta.annotation.PostConstruct;
import java.io.IOException;
import java.io.Reader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.apache.commons.csv.CSVFormat;
import org.apache.commons.csv.CSVParser;
import org.apache.commons.csv.CSVRecord;
import org.springframework.stereotype.Component;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

@Component
public class DataStore {
    private static final List<String> CSV_FILES = List.of(
            "predictions.csv", "teams.csv", "current_form.csv", "team_form.csv");

    private final Path dataDirectory;
    private final JsonMapper jsonMapper;
    private List<Prediction> predictions = List.of();
    private List<Team> teams = List.of();
    private Map<String, TeamForm> teamForms = Map.of();
    private ModelInfo modelInfo;

    public DataStore(DataProperties properties, JsonMapper jsonMapper) {
        this.dataDirectory = Path.of(properties.dataDirectory()).toAbsolutePath().normalize();
        this.jsonMapper = jsonMapper;
    }

    @PostConstruct
    void load() {
        try {
            JsonNode contract = jsonMapper.readTree(dataDirectory.resolve("data_contract.json").toFile());
            for (String filename : CSV_FILES) {
                validateHeaders(filename, contract);
            }
            validateModelInfoProperties(contract);
            predictions = List.copyOf(loadPredictions());
            teams = loadTeams().stream().sorted(Comparator.comparing(Team::name)).toList();
            teamForms = Map.copyOf(loadTeamForms());
            modelInfo = loadModelInfo();
            validateRelationships();
        } catch (DataContractException exception) {
            throw exception;
        } catch (Exception exception) {
            throw new DataContractException(
                    "Could not load prediction data from " + dataDirectory + ": " + exception.getMessage(),
                    exception);
        }
    }

    public List<Prediction> predictions() {
        return predictions;
    }

    public List<Team> teams() {
        return teams;
    }

    public Map<String, TeamForm> teamForms() {
        return teamForms;
    }

    public ModelInfo modelInfo() {
        return modelInfo;
    }

    private void validateHeaders(String filename, JsonNode contract) throws IOException {
        List<String> required = new ArrayList<>();
        for (JsonNode node : contract.path("csvFiles").path(filename).path("requiredColumns")) {
            required.add(node.asText());
        }
        if (required.isEmpty()) {
            throw new DataContractException("No contract definition found for " + filename);
        }
        try (Reader reader = Files.newBufferedReader(dataDirectory.resolve(filename), StandardCharsets.UTF_8);
             CSVParser parser = CSVFormat.DEFAULT.builder().setHeader().setSkipHeaderRecord(true).get().parse(reader)) {
            Set<String> missing = new HashSet<>(required);
            missing.removeAll(parser.getHeaderMap().keySet());
            if (!missing.isEmpty()) {
                throw new DataContractException(filename + " is missing required columns: " + missing);
            }
        }
    }

    private void validateModelInfoProperties(JsonNode contract) throws IOException {
        JsonNode info = jsonMapper.readTree(dataDirectory.resolve("model_info.json").toFile());
        List<String> missing = new ArrayList<>();
        for (JsonNode property : contract.path("jsonFiles").path("model_info.json")
                .path("requiredProperties")) {
            if (!info.has(property.asText())) {
                missing.add(property.asText());
            }
        }
        if (!missing.isEmpty()) {
            throw new DataContractException("model_info.json is missing required properties: " + missing);
        }
    }

    private List<CSVRecord> readCsv(String filename) throws IOException {
        try (Reader reader = Files.newBufferedReader(dataDirectory.resolve(filename), StandardCharsets.UTF_8);
             CSVParser parser = CSVFormat.DEFAULT.builder().setHeader().setSkipHeaderRecord(true).get().parse(reader)) {
            return parser.getRecords();
        }
    }

    private List<Prediction> loadPredictions() throws IOException {
        List<Prediction> loaded = new ArrayList<>();
        Set<String> gameIds = new HashSet<>();
        for (CSVRecord row : readCsv("predictions.csv")) {
            String gameId = row.get("game_id");
            if (!gameIds.add(gameId)) {
                throw new DataContractException("predictions.csv contains duplicate game_id: " + gameId);
            }
            double probability = decimal(row, "home_win_prob");
            double confidence = decimal(row, "confidence");
            if (probability < 0 || probability > 1 || confidence < 0.5 || confidence > 1) {
                throw new DataContractException("Invalid probability for game " + gameId);
            }
            loaded.add(new Prediction(
                    gameId, integer(row, "season"), integer(row, "week"),
                    LocalDate.parse(row.get("gameday")), row.get("away_team"), row.get("home_team"),
                    nullableDecimal(row, "away_score"), nullableDecimal(row, "home_score"),
                    nullableDecimal(row, "result"), nullableDecimal(row, "spread_line"),
                    bool(row, "div_game"), bool(row, "is_played"), probability,
                    row.get("predicted_winner"), confidence, nullableText(row, "actual_winner"),
                    nullableBoolean(row, "was_correct"), decimal(row, "home_off_epa"),
                    decimal(row, "home_def_epa"), decimal(row, "home_plays"),
                    decimal(row, "away_off_epa"), decimal(row, "away_def_epa"),
                    decimal(row, "away_plays"), decimal(row, "off_epa_diff"),
                    decimal(row, "def_epa_diff"), decimal(row, "pace_diff"),
                    decimal(row, "rest_diff")));
        }
        return loaded;
    }

    private List<Team> loadTeams() throws IOException {
        List<Team> loaded = new ArrayList<>();
        Set<String> abbreviations = new HashSet<>();
        for (CSVRecord row : readCsv("teams.csv")) {
            String abbreviation = row.get("team_abbr");
            if (!abbreviations.add(abbreviation)) {
                throw new DataContractException("teams.csv contains duplicate team: " + abbreviation);
            }
            loaded.add(new Team(abbreviation, row.get("team_name"), row.get("team_nick"),
                    row.get("team_conf"), row.get("team_division"), row.get("team_color"),
                    row.get("team_logo_espn")));
        }
        return loaded;
    }

    private Map<String, TeamForm> loadTeamForms() throws IOException {
        List<TeamForm> forms = new ArrayList<>();
        for (CSVRecord row : readCsv("current_form.csv")) {
            forms.add(new TeamForm(row.get("team"), decimal(row, "form_off_epa"),
                    decimal(row, "form_def_epa"), decimal(row, "form_plays"),
                    integer(row, "games_used"), LocalDate.parse(row.get("form_through")), 0, 0));
        }
        List<TeamForm> offense = forms.stream()
                .sorted(Comparator.comparingDouble(TeamForm::offensiveEpa).reversed()).toList();
        List<TeamForm> defense = forms.stream()
                .sorted(Comparator.comparingDouble(TeamForm::defensiveEpa)).toList();
        Map<String, Integer> offenseRanks = ranks(offense);
        Map<String, Integer> defenseRanks = ranks(defense);
        Map<String, TeamForm> ranked = new HashMap<>();
        for (TeamForm form : forms) {
            ranked.put(form.team(), form.withRanks(
                    offenseRanks.get(form.team()), defenseRanks.get(form.team())));
        }
        return ranked;
    }

    private Map<String, Integer> ranks(List<TeamForm> forms) {
        Map<String, Integer> result = new HashMap<>();
        for (int index = 0; index < forms.size(); index++) {
            result.put(forms.get(index).team(), index + 1);
        }
        return result;
    }

    private ModelInfo loadModelInfo() throws IOException {
        JsonNode root = jsonMapper.readTree(dataDirectory.resolve("model_info.json").toFile());
        JsonNode matrix = root.path("confusion_matrix");
        ConfusionMatrix confusionMatrix = new ConfusionMatrix(
                matrix.path("true_negative").asInt(), matrix.path("false_positive").asInt(),
                matrix.path("false_negative").asInt(), matrix.path("true_positive").asInt());
        List<ConfidenceBucket> buckets = new ArrayList<>();
        for (JsonNode bucket : root.path("confidence_buckets")) {
            buckets.add(new ConfidenceBucket(bucket.path("bucket").asText(), bucket.path("games").asInt(),
                    nullableNodeDouble(bucket.path("accuracy")),
                    nullableNodeDouble(bucket.path("average_confidence"))));
        }
        List<String> features = new ArrayList<>();
        root.path("features").forEach(node -> features.add(node.asText()));
        List<String> limitations = new ArrayList<>();
        root.path("limitations").forEach(node -> limitations.add(node.asText()));
        Map<String, Double> coefficients = new LinkedHashMap<>();
        root.path("coefficients").properties()
                .forEach(entry -> coefficients.put(entry.getKey(), entry.getValue().asDouble()));
        return new ModelInfo(root.path("built_on").asText(), root.path("train_seasons").asText(),
                root.path("test_seasons").asText(), root.path("train_games").asInt(),
                root.path("test_games").asInt(), root.path("accuracy").asDouble(),
                root.path("baseline").asDouble(), root.path("roc_auc").asDouble(),
                root.path("log_loss").asDouble(), confusionMatrix, root.path("form_through").asText(),
                root.path("upcoming_season").asInt(), root.path("form_window").asInt(),
                root.path("minimum_form_games").asInt(), List.copyOf(features),
                Map.copyOf(coefficients), List.copyOf(buckets), List.copyOf(limitations));
    }

    private void validateRelationships() {
        Set<String> abbreviations = new HashSet<>();
        teams.forEach(team -> abbreviations.add(team.abbreviation()));
        for (Prediction prediction : predictions) {
            if (!abbreviations.contains(prediction.homeTeam())
                    || !abbreviations.contains(prediction.awayTeam())) {
                throw new DataContractException(
                        "Prediction references an unknown team: " + prediction.gameId());
            }
        }
        if (!teamForms.keySet().equals(abbreviations)) {
            throw new DataContractException("current_form.csv and teams.csv have different team sets");
        }
    }

    private int integer(CSVRecord row, String column) {
        return Integer.parseInt(row.get(column));
    }

    private double decimal(CSVRecord row, String column) {
        return Double.parseDouble(row.get(column));
    }

    private Double nullableDecimal(CSVRecord row, String column) {
        String value = row.get(column);
        return value == null || value.isBlank() ? null : Double.valueOf(value);
    }

    private String nullableText(CSVRecord row, String column) {
        String value = row.get(column);
        return value == null || value.isBlank() ? null : value;
    }

    private boolean bool(CSVRecord row, String column) {
        String value = row.get(column);
        if (value.equalsIgnoreCase("true") || value.equals("1")) {
            return true;
        }
        if (value.equalsIgnoreCase("false") || value.equals("0")) {
            return false;
        }
        throw new DataContractException("Invalid boolean in " + column + ": " + value);
    }

    private Boolean nullableBoolean(CSVRecord row, String column) {
        return row.get(column).isBlank() ? null : bool(row, column);
    }

    private Double nullableNodeDouble(JsonNode node) {
        return node.isNull() ? null : node.asDouble();
    }
}
