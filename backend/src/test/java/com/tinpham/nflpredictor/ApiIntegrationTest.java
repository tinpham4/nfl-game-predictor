package com.tinpham.nflpredictor;

import static org.hamcrest.Matchers.everyItem;
import static org.hamcrest.Matchers.greaterThanOrEqualTo;
import static org.hamcrest.Matchers.hasSize;
import static org.hamcrest.Matchers.lessThanOrEqualTo;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.test.web.servlet.MockMvc;

@SpringBootTest
@AutoConfigureMockMvc
class ApiIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

    @Test
    void applicationStartsAndHealthEndpointWorks() throws Exception {
        mockMvc.perform(get("/api/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("ok"))
                .andExpect(jsonPath("$.teams").value(32));
    }

    @Test
    void dashboardIsServedBySpringBoot() throws Exception {
        mockMvc.perform(get("/index.html"))
                .andExpect(status().isOk())
                .andExpect(content().string(org.hamcrest.Matchers.containsString(
                        "NFL Game Predictor")));
    }

    @Test
    void teamsAndValidTeamLoad() throws Exception {
        mockMvc.perform(get("/api/teams"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(32)));
        mockMvc.perform(get("/api/teams/MIN"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.team.abbreviation").value("MIN"))
                .andExpect(jsonPath("$.form.offensiveRank").isNumber())
                .andExpect(jsonPath("$.standing.projectedWins").isNumber());
    }

    @Test
    void invalidAndMalformedTeamsReturnUsefulErrors() throws Exception {
        mockMvc.perform(get("/api/teams/XYZ"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.message").value("Team not found: XYZ"));
        mockMvc.perform(get("/api/teams/not-a-team"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.message").exists());
    }

    @Test
    void predictionsLoadAndProbabilitiesParse() throws Exception {
        mockMvc.perform(get("/api/predictions").param("season", "2026"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].homeWinProbability", greaterThanOrEqualTo(0.0)))
                .andExpect(jsonPath("$[0].homeWinProbability", lessThanOrEqualTo(1.0)));
    }

    @Test
    void standingsAndModelInfoLoad() throws Exception {
        mockMvc.perform(get("/api/standings"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(32)))
                .andExpect(jsonPath("$[*].games", everyItem(greaterThanOrEqualTo(17))));
        mockMvc.perform(get("/api/model"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.accuracy").isNumber())
                .andExpect(jsonPath("$.confidenceBuckets", hasSize(5)));
    }

    @Test
    void malformedFiltersReturnBadRequest() throws Exception {
        mockMvc.perform(get("/api/predictions").param("week", "99"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.message").value("week must be between 1 and 22"));
        mockMvc.perform(get("/api/predictions").param("season", "football"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.message").exists());
    }
}
