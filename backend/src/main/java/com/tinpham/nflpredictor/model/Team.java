package com.tinpham.nflpredictor.model;

public record Team(
        String abbreviation,
        String name,
        String nickname,
        String conference,
        String division,
        String color,
        String logoUrl
) {
}
