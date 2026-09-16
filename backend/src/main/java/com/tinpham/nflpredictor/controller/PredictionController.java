package com.tinpham.nflpredictor.controller;

import com.tinpham.nflpredictor.model.Prediction;
import com.tinpham.nflpredictor.service.PredictionService;
import java.util.List;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/predictions")
public class PredictionController {
    private final PredictionService predictionService;

    public PredictionController(PredictionService predictionService) {
        this.predictionService = predictionService;
    }

    @GetMapping
    public List<Prediction> predictions(
            @RequestParam(required = false) Integer season,
            @RequestParam(required = false) Integer week,
            @RequestParam(required = false) Boolean played,
            @RequestParam(required = false) String team) {
        return predictionService.find(season, week, played, team);
    }

    @GetMapping("/week/{week}")
    public List<Prediction> byWeek(
            @PathVariable int week, @RequestParam(required = false) Integer season) {
        return predictionService.find(season, week, null, null);
    }

    @GetMapping("/team/{team}")
    public List<Prediction> byTeam(
            @PathVariable String team,
            @RequestParam(required = false) Integer season,
            @RequestParam(required = false) Boolean played) {
        return predictionService.find(season, null, played, team);
    }
}
