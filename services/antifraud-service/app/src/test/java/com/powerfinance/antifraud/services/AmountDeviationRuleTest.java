package com.powerfinance.antifraud.services;

import static com.powerfinance.antifraud.services.RuleTestSupport.harnessFor;
import static com.powerfinance.antifraud.services.RuleTestSupport.nonTransactionEvent;
import static com.powerfinance.antifraud.services.RuleTestSupport.transactionEvent;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.powerfinance.antifraud.types.OutboxEvent;
import org.apache.flink.streaming.util.KeyedOneInputStreamOperatorTestHarness;
import org.junit.jupiter.api.Test;

class AmountDeviationRuleTest {

    private void feedNormalHistory(
            KeyedOneInputStreamOperatorTestHarness<String, OutboxEvent, String> harness,
            String clerkId,
            int count) throws Exception {
        for (int i = 0; i < count; i++) {
            harness.processElement(transactionEvent(clerkId, i % 2 == 0 ? "95" : "105"), 0);
        }
    }

    @Test
    void flagsOutlierAfterWarmup() throws Exception {
        var harness = harnessFor(new AmountDeviationRule(), 0.0);

        feedNormalHistory(harness, "u1", 40);
        assertTrue(harness.extractOutputValues().isEmpty(), "normal activity must not alert");

        harness.processElement(transactionEvent("u1", "1000"), 0);

        var alerts = harness.extractOutputValues();
        assertEquals(1, alerts.size());
        assertTrue(alerts.get(0).contains("AmountDeviationRule"), alerts.get(0));
        harness.close();
    }

    @Test
    void doesNotFlagAmountWithinDeviation() throws Exception {
        var harness = harnessFor(new AmountDeviationRule(), 0.0);

        feedNormalHistory(harness, "u1", 40);
        harness.processElement(transactionEvent("u1", "104"), 0);

        assertTrue(harness.extractOutputValues().isEmpty());
        harness.close();
    }

    @Test
    void doesNotFlagBeforeWarmup() throws Exception {
        var harness = harnessFor(new AmountDeviationRule(), 0.0);

        feedNormalHistory(harness, "u1", 10);
        harness.processElement(transactionEvent("u1", "100000"), 0);

        assertTrue(harness.extractOutputValues().isEmpty(), "must stay quiet until warmed up");
        harness.close();
    }

    @Test
    void keepsPerUserDistributionsSeparate() throws Exception {
        var harness = harnessFor(new AmountDeviationRule(), 0.0);

        feedNormalHistory(harness, "u1", 40);
        harness.processElement(transactionEvent("u2", "1000"), 0);

        assertTrue(harness.extractOutputValues().isEmpty());
        harness.close();
    }

    @Test
    void ignoresNonTransactionEvents() throws Exception {
        var harness = harnessFor(new AmountDeviationRule(), 0.0);

        for (int i = 0; i < 50; i++) {
            harness.processElement(nonTransactionEvent("u1"), 0);
        }

        assertTrue(harness.extractOutputValues().isEmpty());
        harness.close();
    }
}
