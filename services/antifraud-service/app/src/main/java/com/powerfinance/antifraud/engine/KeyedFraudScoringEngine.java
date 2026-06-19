package com.powerfinance.antifraud.engine;

import java.util.List;

import com.powerfinance.antifraud.model.Alert;
import com.powerfinance.antifraud.model.OutboxEvent;
import com.powerfinance.antifraud.rules.FraudRule;
import org.apache.flink.api.common.functions.OpenContext;
import org.apache.flink.streaming.api.datastream.DataStream;
import org.apache.flink.streaming.api.functions.KeyedProcessFunction;
import org.apache.flink.util.Collector;

/** Per-user keyed engine that sums every rule's score and emits an alert past the threshold. */
public class KeyedFraudScoringEngine
        extends KeyedProcessFunction<String, OutboxEvent, Alert>
        implements FraudScoringEngine {

    private final List<FraudRule> fraudRules;
    private final double fraudScoreThreshold;

    public KeyedFraudScoringEngine(List<FraudRule> fraudRules, double fraudScoreThreshold) {
        this.fraudRules = fraudRules;
        this.fraudScoreThreshold = fraudScoreThreshold;
    }

    /** Keys the events by Clerk id and runs them through this scoring process function. */
    @Override
    public DataStream<Alert> score(DataStream<OutboxEvent> events) {
        return events.keyBy(OutboxEvent::getClerkId).process(this);
    }

    /** Opens every configured rule with the runtime context so they can register state. */
    @Override
    public void open(OpenContext openContext) throws Exception {
        for (FraudRule fraudRule : fraudRules) {
            fraudRule.open(getRuntimeContext());
        }
    }

    /** Scores the event across all rules and emits an alert when the summed score exceeds the threshold. */
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
                    outboxEvent.getEventId(),
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
