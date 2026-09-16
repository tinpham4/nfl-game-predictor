package com.tinpham.nflpredictor.service;

import com.tinpham.nflpredictor.exception.BadRequestException;
import com.tinpham.nflpredictor.exception.ResourceNotFoundException;
import com.tinpham.nflpredictor.model.Prediction;
import java.util.Comparator;
import java.util.List;
import org.springframework.stereotype.Service;

@Service
public class PredictionService {
    private final DataStore dataStore;

    public PredictionService(DataStore dataStore) {
        this.dataStore = dataStore;
    }

    public List<Prediction> find(Integer season, Integer week, Boolean played, String team) {
        if (season != null && (season < 1920 || season > 2100)) {
            throw new BadRequestException("season must be between 1920 and 2100");
        }
        if (week != null && (week < 1 || week > 22)) {
            throw new BadRequestException("week must be between 1 and 22");
        }
        String normalizedTeam = team == null ? null : TeamService.normalizeTeam(team);
        if (normalizedTeam != null && dataStore.teams().stream()
                .noneMatch(item -> item.abbreviation().equals(normalizedTeam))) {
            throw new ResourceNotFoundException("Team not found: " + normalizedTeam);
        }
        return dataStore.predictions().stream()
                .filter(game -> season == null || game.season() == season)
                .filter(game -> week == null || game.week() == week)
                .filter(game -> played == null || game.played() == played)
                .filter(game -> normalizedTeam == null
                        || game.homeTeam().equals(normalizedTeam)
                        || game.awayTeam().equals(normalizedTeam))
                .sorted(Comparator.comparing(Prediction::gameday).thenComparing(Prediction::gameId))
                .toList();
    }
}
