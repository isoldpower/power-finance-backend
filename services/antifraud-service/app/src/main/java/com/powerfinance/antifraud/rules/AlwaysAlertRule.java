package com.powerfinance.antifraud.rules;

import com.powerfinance.antifraud.model.OutboxEvent;
import org.apache.flink.api.common.functions.RuntimeContext;

/** Demo rule that scores every event high enough to always trigger an alert. */
public class AlwaysAlertRule implements FraudRule {

    private static final double WEIGHT = 100.0;

    /** Holds no state and requires no initialisation. */
    @Override
    public void open(RuntimeContext runtimeContext) {
    }

    /** Returns a fixed high score for every event. */
    @Override
    public double score(OutboxEvent outboxEvent) {
        return WEIGHT;
    }
}
