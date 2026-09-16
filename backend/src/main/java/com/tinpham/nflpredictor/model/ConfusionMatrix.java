package com.tinpham.nflpredictor.model;

public record ConfusionMatrix(
        int trueNegative,
        int falsePositive,
        int falseNegative,
        int truePositive
) {
}
