package com.tinpham.nflpredictor.model;

public record ConfidenceBucket(
        String bucket,
        int games,
        Double accuracy,
        Double averageConfidence
) {
}
