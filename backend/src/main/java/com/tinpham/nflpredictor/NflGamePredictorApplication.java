package com.tinpham.nflpredictor;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.ConfigurationPropertiesScan;

@SpringBootApplication
@ConfigurationPropertiesScan
public class NflGamePredictorApplication {

    public static void main(String[] args) {
        SpringApplication.run(NflGamePredictorApplication.class, args);
    }
}
