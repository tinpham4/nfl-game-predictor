package com.tinpham.nflpredictor.service;

import com.tinpham.nflpredictor.dto.TeamDetails;
import com.tinpham.nflpredictor.exception.BadRequestException;
import com.tinpham.nflpredictor.exception.ResourceNotFoundException;
import com.tinpham.nflpredictor.model.Prediction;
import com.tinpham.nflpredictor.model.Team;
import com.tinpham.nflpredictor.model.TeamForm;
import java.util.List;
import java.util.Locale;
import org.springframework.stereotype.Service;

@Service
public class TeamService {
    private final DataStore dataStore;
    private final PredictionService predictionService;
    private final StandingsService standingsService;

    public TeamService(
            DataStore dataStore,
            PredictionService predictionService,
            StandingsService standingsService) {
        this.dataStore = dataStore;
        this.predictionService = predictionService;
        this.standingsService = standingsService;
    }

    public List<Team> all() {
        return dataStore.teams();
    }

    public TeamDetails details(String abbreviation) {
        String team = normalizeTeam(abbreviation);
        Team found = dataStore.teams().stream()
                .filter(item -> item.abbreviation().equals(team))
                .findFirst()
                .orElseThrow(() -> new ResourceNotFoundException("Team not found: " + team));
        return new TeamDetails(found, form(team), standingsService.forTeam(team));
    }

    public TeamForm form(String abbreviation) {
        String team = normalizeTeam(abbreviation);
        TeamForm form = dataStore.teamForms().get(team);
        if (form == null) {
            throw new ResourceNotFoundException("Team form not found: " + team);
        }
        return form;
    }

    public List<Prediction> games(String abbreviation, Integer season, Boolean played) {
        return predictionService.find(season, null, played, normalizeTeam(abbreviation));
    }

    static String normalizeTeam(String abbreviation) {
        String team = abbreviation == null ? "" : abbreviation.trim().toUpperCase(Locale.US);
        if (!team.matches("[A-Z]{2,3}")) {
            throw new BadRequestException("team must be a two- or three-letter abbreviation");
        }
        return team;
    }
}
