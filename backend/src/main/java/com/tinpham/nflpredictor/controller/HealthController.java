package com.tinpham.nflpredictor.controller;

import com.tinpham.nflpredictor.service.DataStore;
import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/health")
public class HealthController {
    private final DataStore dataStore;

    public HealthController(DataStore dataStore) {
        this.dataStore = dataStore;
    }

    @GetMapping
    public Map<String, Object> health() {
        return Map.of("status", "ok", "teams", dataStore.teams().size(),
                "predictions", dataStore.predictions().size());
    }
}
