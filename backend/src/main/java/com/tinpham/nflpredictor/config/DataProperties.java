package com.tinpham.nflpredictor.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "nfl")
public record DataProperties(String dataDirectory) {
}
