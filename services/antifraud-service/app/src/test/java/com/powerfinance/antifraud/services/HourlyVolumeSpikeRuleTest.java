package com.powerfinance.antifraud.services;

import static com.powerfinance.antifraud.services.RuleTestSupport.harnessFor;
import static com.powerfinance.antifraud.services.RuleTestSupport.transactionEvent;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.powerfinance.antifraud.types.Alert;
import com.powerfinance.antifraud.types.OutboxEvent;
import org.apache.flink.streaming.util.KeyedOneInputStreamOperatorTestHarness;
import org.junit.jupiter.api.Test;

class HourlyVolumeSpikeRuleTest {

    private static final long DAY_SECONDS = 24 * 3_600L;
    private static final long BASE_SECONDS = 30 * DAY_SECONDS;

    private void feedDailyBaseline(
            KeyedOneInputStreamOperatorTestHarness<String, OutboxEvent, Alert> harness,
            String clerkId,
            int days,
            String dailyAmount) throws Exception {
        for (int day = 0; day < days; day++) {
            harness.processElement(
                    transactionEvent(clerkId, dailyAmount, BASE_SECONDS + day * DAY_SECONDS), 0);
        }
    }

    @Test
    void flagsVolumeSpikeAgainstMonthlyBaseline() throws Exception {
        var harness = harnessFor(new HourlyVolumeSpikeRule(), 0.0);

        feedDailyBaseline(harness, "u1", 10, "100");
        assertTrue(harness.extractOutputValues().isEmpty(), "steady baseline must not alert");

        harness.processElement(
                transactionEvent("u1", "1000", BASE_SECONDS + 10 * DAY_SECONDS), 0);

        var alerts = harness.extractOutputValues();
        assertEquals(1, alerts.size());
        assertTrue(alerts.get(0).message.contains("HourlyVolumeSpikeRule"), alerts.get(0).message);
        harness.close();
    }

    @Test
    void doesNotFlagSteadyVolume() throws Exception {
        var harness = harnessFor(new HourlyVolumeSpikeRule(), 0.0);

        feedDailyBaseline(harness, "u1", 10, "100");
        harness.processElement(
                transactionEvent("u1", "100", BASE_SECONDS + 10 * DAY_SECONDS), 0);

        assertTrue(harness.extractOutputValues().isEmpty());
        harness.close();
    }

    @Test
    void doesNotFlagBeforeBaselineEstablished() throws Exception {
        var harness = harnessFor(new HourlyVolumeSpikeRule(), 0.0);

        feedDailyBaseline(harness, "u1", 3, "100");
        harness.processElement(
                transactionEvent("u1", "100000", BASE_SECONDS + 3 * DAY_SECONDS), 0);

        assertTrue(harness.extractOutputValues().isEmpty(), "too little history to judge");
        harness.close();
    }
}
