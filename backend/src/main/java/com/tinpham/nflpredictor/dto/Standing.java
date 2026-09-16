package com.tinpham.nflpredictor.dto;

public record Standing(
        int rank,
        String team,
        String teamName,
        String conference,
        String division,
        int games,
        double projectedWins,
        double projectedLosses
) {
}
