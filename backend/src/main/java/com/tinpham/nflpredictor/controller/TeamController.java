package com.tinpham.nflpredictor.controller;

import com.tinpham.nflpredictor.dto.TeamDetails;
import com.tinpham.nflpredictor.model.Prediction;
import com.tinpham.nflpredictor.model.Team;
import com.tinpham.nflpredictor.model.TeamForm;
import com.tinpham.nflpredictor.service.TeamService;
import java.util.List;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/teams")
public class TeamController {
    private final TeamService teamService;

    public TeamController(TeamService teamService) {
        this.teamService = teamService;
    }

    @GetMapping
    public List<Team> teams() {
        return teamService.all();
    }

    @GetMapping("/{team}")
    public TeamDetails team(@PathVariable String team) {
        return teamService.details(team);
    }

    @GetMapping("/{team}/games")
    public List<Prediction> games(
            @PathVariable String team,
            @RequestParam(required = false) Integer season,
            @RequestParam(required = false) Boolean played) {
        return teamService.games(team, season, played);
    }

    @GetMapping("/{team}/form")
    public TeamForm form(@PathVariable String team) {
        return teamService.form(team);
    }
}
