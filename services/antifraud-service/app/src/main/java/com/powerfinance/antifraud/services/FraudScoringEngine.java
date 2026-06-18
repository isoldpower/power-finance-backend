package com.powerfinance.antifraud.services;

import java.util.List;

import com.powerfinance.antifraud.types.Alert;
import com.powerfinance.antifraud.types.OutboxEvent;
import org.apache.flink.api.common.functions.OpenContext;
import org.apache.flink.streaming.api.functions.KeyedProcessFunction;
import org.apache.flink.util.Collector;

public class FraudScoringEngine extends KeyedProcessFunction<String, OutboxEvent, Alert> {

    private final List<FraudRule> fraudRules;
    private final double fraudScoreThreshold;

    public FraudScoringEngine(List<FraudRule> fraudRules, double fraudScoreThreshold) {
        this.fraudRules = fraudRules;
        this.fraudScoreThreshold = fraudScoreThreshold;
    }

    @Override
    public void open(OpenContext openContext) throws Exception {
        for (FraudRule fraudRule : fraudRules) {
            fraudRule.open(getRuntimeContext());
        }
    }

    @Override
    public void processElement(
            OutboxEvent outboxEvent,
            Context context,
            Collector<Alert> alertOutput
    ) throws Exception {
        double totalFraudScore = 0;
        StringBuilder scoreBreakdown = new StringBuilder();
        for (FraudRule fraudRule : fraudRules) {
            double rulePoints = fraudRule.score(outboxEvent);
            if (rulePoints > 0) {
                totalFraudScore += rulePoints;
                scoreBreakdown
                        .append(fraudRule.getClass().getSimpleName())
                        .append('=')
                        .append(rulePoints)
                        .append(' ');
            }
        }

        if (totalFraudScore > fraudScoreThreshold) {
            String currentKey = context.getCurrentKey();
            alertOutput.collect(new Alert(currentKey, this.buildAlertMessage(
                    currentKey,
                    outboxEvent.eventId,
                    totalFraudScore,
                    scoreBreakdown.toString().trim()
            )));
        }
    }

    private String buildAlertMessage(
            String currentKey,
            String eventId,
            double score,
            String scoreBreakdown
        ) {
        return "FRAUD clerk=" + currentKey
                + " event=" + eventId
                + " score=" + score
                + " threshold=" + fraudScoreThreshold
                + " [" + scoreBreakdown + "]";
    }
}
