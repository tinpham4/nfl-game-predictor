package com.tinpham.nflpredictor;

import static org.assertj.core.api.Assertions.assertThat;

import com.tinpham.nflpredictor.dto.Standing;
import com.tinpham.nflpredictor.service.StandingsService;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

@SpringBootTest
class StandingsServiceTest {

    @Autowired
    private StandingsService standingsService;

    @Test
    void projectedWinsAndLossesCoverTheSeason() {
        List<Standing> standings = standingsService.all(null);

        assertThat(standings).hasSize(32);
        assertThat(standings).allSatisfy(row ->
                assertThat(row.projectedWins() + row.projectedLosses()).isEqualTo(row.games()));
        assertThat(standings).isSortedAccordingTo(
                (left, right) -> Double.compare(right.projectedWins(), left.projectedWins()));
    }
}
