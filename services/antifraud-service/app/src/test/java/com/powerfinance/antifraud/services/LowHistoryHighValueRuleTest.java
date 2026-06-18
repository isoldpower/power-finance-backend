package com.powerfinance.antifraud.services;

import static com.powerfinance.antifraud.services.RuleTestSupport.harnessFor;
import static com.powerfinance.antifraud.services.RuleTestSupport.nonTransactionEvent;
import static com.powerfinance.antifraud.services.RuleTestSupport.transactionEvent;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

class LowHistoryHighValueRuleTest {

    @Test
    void flagsLargeTransactionOnThinHistory() throws Exception {
        var harness = harnessFor(new LowHistoryHighValueRule(), 0.0);

        harness.processElement(transactionEvent("u1", "2000"), 0);

        var alerts = harness.extractOutputValues();
        assertEquals(1, alerts.size());
        assertTrue(alerts.get(0).contains("LowHistoryHighValueRule"), alerts.get(0));
        harness.close();
    }

    @Test
    void doesNotFlagSmallTransactionOnThinHistory() throws Exception {
        var harness = harnessFor(new LowHistoryHighValueRule(), 0.0);

        harness.processElement(transactionEvent("u1", "50"), 0);

        assertTrue(harness.extractOutputValues().isEmpty());
        harness.close();
    }

    @Test
    void doesNotFlagLargeTransactionOnEstablishedHistory() throws Exception {
        var harness = harnessFor(new LowHistoryHighValueRule(), 0.0);

        harness.processElement(transactionEvent("u1", "60"), 0);
        harness.processElement(transactionEvent("u1", "60"), 0);
        harness.processElement(transactionEvent("u1", "2000"), 0);

        assertTrue(harness.extractOutputValues().isEmpty());
        harness.close();
    }

    @Test
    void keepsPerUserHistorySeparate() throws Exception {
        var harness = harnessFor(new LowHistoryHighValueRule(), 0.0);

        harness.processElement(transactionEvent("u1", "60"), 0);
        harness.processElement(transactionEvent("u1", "60"), 0);
        harness.processElement(transactionEvent("u2", "2000"), 0);

        var alerts = harness.extractOutputValues();
        assertEquals(1, alerts.size());
        assertTrue(alerts.get(0).contains("clerk=u2"), alerts.get(0));
        harness.close();
    }

    @Test
    void ignoresNonTransactionEvents() throws Exception {
        var harness = harnessFor(new LowHistoryHighValueRule(), 0.0);

        harness.processElement(nonTransactionEvent("u1"), 0);

        assertTrue(harness.extractOutputValues().isEmpty());
        harness.close();
    }
}
