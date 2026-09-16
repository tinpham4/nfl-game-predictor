package com.tinpham.nflpredictor.service;

import com.tinpham.nflpredictor.dto.ModelPerformance;
import com.tinpham.nflpredictor.model.ModelInfo;
import org.springframework.stereotype.Service;

@Service
public class ModelInfoService {
    private final DataStore dataStore;

    public ModelInfoService(DataStore dataStore) {
        this.dataStore = dataStore;
    }

    public ModelInfo get() {
        return dataStore.modelInfo();
    }

    public ModelPerformance performance() {
        ModelInfo info = get();
        return new ModelPerformance(info.accuracy(), info.baseline(), info.rocAuc(),
                info.logLoss(), info.testGames(), info.confusionMatrix(), info.confidenceBuckets());
    }
}
