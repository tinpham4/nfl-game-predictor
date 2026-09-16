package com.tinpham.nflpredictor.controller;

import com.tinpham.nflpredictor.dto.ModelPerformance;
import com.tinpham.nflpredictor.model.ModelInfo;
import com.tinpham.nflpredictor.service.ModelInfoService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/model")
public class ModelController {
    private final ModelInfoService modelInfoService;

    public ModelController(ModelInfoService modelInfoService) {
        this.modelInfoService = modelInfoService;
    }

    @GetMapping
    public ModelInfo model() {
        return modelInfoService.get();
    }

    @GetMapping("/performance")
    public ModelPerformance performance() {
        return modelInfoService.performance();
    }
}
