package com.tinpham.nflpredictor.service;

import com.tinpham.nflpredictor.dto.Standing;
import com.tinpham.nflpredictor.exception.ResourceNotFoundException;
import com.tinpham.nflpredictor.model.Prediction;
import com.tinpham.nflpredictor.model.Team;
import jakarta.annotation.PostConstruct;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import org.springframework.stereotype.Service;

@Service
public class StandingsService {
    private final DataStore dataStore;
    private List<Standing> standings = List.of();

    public StandingsService(DataStore dataStore) {
        this.dataStore = dataStore;
    }

    @PostConstruct
    void calculate() {
        int season = dataStore.modelInfo().upcomingSeason();
        Map<String, Double> wins = new HashMap<>();
        Map<String, Integer> games = new HashMap<>();
        for (Prediction prediction : dataStore.predictions()) {
            if (prediction.season() != season) {
                continue;
            }
            double homeWinValue = prediction.played()
                    ? (prediction.homeTeam().equals(prediction.actualWinner()) ? 1.0 : 0.0)
                    : prediction.homeWinProbability();
            wins.merge(prediction.homeTeam(), homeWinValue, Double::sum);
            wins.merge(prediction.awayTeam(), 1 - homeWinValue, Double::sum);
            games.merge(prediction.homeTeam(), 1, Integer::sum);
            games.merge(prediction.awayTeam(), 1, Integer::sum);
        }
        Map<String, Team> teams = new HashMap<>();
        dataStore.teams().forEach(team -> teams.put(team.abbreviation(), team));
        List<String> order = wins.keySet().stream()
                .sorted(Comparator.<String>comparingDouble(wins::get)
                        .reversed().thenComparing(Comparator.naturalOrder()))
                .toList();
        List<Standing> calculated = new ArrayList<>();
        for (int index = 0; index < order.size(); index++) {
            String abbreviation = order.get(index);
            Team team = teams.get(abbreviation);
            int gameCount = games.get(abbreviation);
            double projectedWins = round(wins.get(abbreviation));
            calculated.add(new Standing(index + 1, abbreviation, team.name(), team.conference(),
                    team.division(), gameCount, projectedWins, round(gameCount - projectedWins)));
        }
        standings = List.copyOf(calculated);
    }

    public List<Standing> all(String conference) {
        if (conference == null || conference.isBlank()) {
            return standings;
        }
        String normalized = conference.trim().toUpperCase();
        if (!normalized.equals("AFC") && !normalized.equals("NFC")) {
            throw new com.tinpham.nflpredictor.exception.BadRequestException(
                    "conference must be AFC or NFC");
        }
        return standings.stream().filter(row -> row.conference().equals(normalized)).toList();
    }

    public Standing forTeam(String team) {
        return standings.stream().filter(row -> row.team().equals(team)).findFirst()
                .orElseThrow(() -> new ResourceNotFoundException(
                        "No remaining projections found for team: " + team));
    }

    private double round(double value) {
        return Math.round(value * 10.0) / 10.0;
    }
}
