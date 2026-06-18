package com.powerfinance.antifraud.services;

import static com.powerfinance.antifraud.services.RuleTestSupport.harnessFor;
import static com.powerfinance.antifraud.services.RuleTestSupport.transactionEvent;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.List;

import com.powerfinance.antifraud.types.OutboxEvent;
import org.apache.flink.api.common.functions.RuntimeContext;
import org.apache.flink.api.common.state.ValueState;
import org.apache.flink.api.common.state.ValueStateDescriptor;
import org.junit.jupiter.api.Test;

class FraudScoringEngineTest {

    @Test
    void alertsWhenSummedScoreExceedsThreshold() throws Exception {
        var harness = harnessFor(List.of(new FixedScoreRule(3.0), new FixedScoreRule(3.0)), 4.0);

        harness.processElement(transactionEvent("u1", "10"), 0);

        var alerts = harness.extractOutputValues();
        assertEquals(1, alerts.size());
        assertTrue(alerts.get(0).message.contains("score=6.0"), alerts.get(0).message);
        harness.close();
    }

    @Test
    void doesNotAlertWhenScoreBelowThreshold() throws Exception {
        var harness = harnessFor(List.of(new FixedScoreRule(2.0)), 4.0);

        harness.processElement(transactionEvent("u1", "10"), 0);

        assertTrue(harness.extractOutputValues().isEmpty());
        harness.close();
    }

    @Test
    void zeroScoringRuleContributesNothing() throws Exception {
        var harness = harnessFor(List.of(new FixedScoreRule(0.0)), 0.0);

        harness.processElement(transactionEvent("u1", "10"), 0);

        assertTrue(harness.extractOutputValues().isEmpty(), "0 points must not push over threshold");
        harness.close();
    }

    @Test
    void breakdownListsOnlyTriggeredRules() throws Exception {
        var harness = harnessFor(List.of(new FixedScoreRule(5.0), new FixedScoreRule(0.0)), 4.0);

        harness.processElement(transactionEvent("u1", "10"), 0);

        var alerts = harness.extractOutputValues();
        assertEquals(1, alerts.size());
        assertTrue(alerts.get(0).message.contains("score=5.0"), alerts.get(0).message);
        assertTrue(alerts.get(0).message.contains("FixedScoreRule=5.0"), alerts.get(0).message);
        harness.close();
    }

    @Test
    void keepsRuleStatePerKey() throws Exception {
        var harness = harnessFor(List.of(new SecondEventRule()), 0.0);

        harness.processElement(transactionEvent("u1", "10"), 0);
        harness.processElement(transactionEvent("u2", "10"), 0);
        harness.processElement(transactionEvent("u1", "10"), 0);

        var alerts = harness.extractOutputValues();
        assertEquals(1, alerts.size());
        assertEquals("u1", alerts.get(0).clerkId);
        harness.close();
    }

    static final class FixedScoreRule implements FraudRule {
        private final double points;

        FixedScoreRule(double points) {
            this.points = points;
        }

        @Override
        public void open(RuntimeContext runtimeContext) {
        }

        @Override
        public double score(OutboxEvent outboxEvent) {
            return points;
        }
    }

    static final class SecondEventRule implements FraudRule {
        private transient ValueState<Boolean> seenState;

        @Override
        public void open(RuntimeContext runtimeContext) {
            this.seenState = runtimeContext.getState(new ValueStateDescriptor<>("seen", Boolean.class));
        }

        @Override
        public double score(OutboxEvent outboxEvent) throws Exception {
            boolean seenBefore = Boolean.TRUE.equals(seenState.value());
            seenState.update(true);
            return seenBefore ? 1.0 : 0.0;
        }
    }
}
