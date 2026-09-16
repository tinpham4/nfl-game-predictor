package com.tinpham.nflpredictor.controller;

import com.tinpham.nflpredictor.dto.Standing;
import com.tinpham.nflpredictor.service.StandingsService;
import java.util.List;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/standings")
public class StandingsController {
    private final StandingsService standingsService;

    public StandingsController(StandingsService standingsService) {
        this.standingsService = standingsService;
    }

    @GetMapping
    public List<Standing> standings(@RequestParam(required = false) String conference) {
        return standingsService.all(conference);
    }
}
