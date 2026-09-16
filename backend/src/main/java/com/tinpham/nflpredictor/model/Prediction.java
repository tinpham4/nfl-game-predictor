package com.tinpham.nflpredictor.model;

import java.time.LocalDate;

public record Prediction(
        String gameId,
        int season,
        int week,
        LocalDate gameday,
        String awayTeam,
        String homeTeam,
        Double awayScore,
        Double homeScore,
        Double result,
        Double spreadLine,
        boolean divisionGame,
        boolean played,
        double homeWinProbability,
        String predictedWinner,
        double confidence,
        String actualWinner,
        Boolean correct,
        double homeOffensiveEpa,
        double homeDefensiveEpa,
        double homePlays,
        double awayOffensiveEpa,
        double awayDefensiveEpa,
        double awayPlays,
        double offensiveEpaDifference,
        double defensiveEpaDifference,
        double paceDifference,
        double restDifference
) {
}
