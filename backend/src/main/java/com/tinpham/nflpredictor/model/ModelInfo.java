package com.tinpham.nflpredictor.model;

import java.util.List;
import java.util.Map;

public record ModelInfo(
        String builtOn,
        String trainSeasons,
        String testSeasons,
        int trainGames,
        int testGames,
        double accuracy,
        double baseline,
        double rocAuc,
        double logLoss,
        ConfusionMatrix confusionMatrix,
        String formThrough,
        int upcomingSeason,
        int formWindow,
        int minimumFormGames,
        List<String> features,
        Map<String, Double> coefficients,
        List<ConfidenceBucket> confidenceBuckets,
        List<String> limitations
) {
}
