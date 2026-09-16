package com.tinpham.nflpredictor.dto;

import com.tinpham.nflpredictor.model.ConfidenceBucket;
import com.tinpham.nflpredictor.model.ConfusionMatrix;
import java.util.List;

public record ModelPerformance(
        double accuracy,
        double baseline,
        double rocAuc,
        double logLoss,
        int testGames,
        ConfusionMatrix confusionMatrix,
        List<ConfidenceBucket> confidenceBuckets
) {
}
