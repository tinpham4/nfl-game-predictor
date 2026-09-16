package com.tinpham.nflpredictor.model;

import java.time.LocalDate;

public record TeamForm(
        String team,
        double offensiveEpa,
        double defensiveEpa,
        double plays,
        int gamesUsed,
        LocalDate formThrough,
        int offensiveRank,
        int defensiveRank
) {
    public TeamForm withRanks(int offenseRank, int defenseRank) {
        return new TeamForm(team, offensiveEpa, defensiveEpa, plays, gamesUsed,
                formThrough, offenseRank, defenseRank);
    }
}
