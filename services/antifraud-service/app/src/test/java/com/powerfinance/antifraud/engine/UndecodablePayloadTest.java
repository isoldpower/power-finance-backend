package com.powerfinance.antifraud.engine;

import static com.powerfinance.antifraud.rules.RuleTestSupport.harnessFor;
import static com.powerfinance.antifraud.rules.RuleTestSupport.transactionEvent;
import static com.powerfinance.antifraud.rules.RuleTestSupport.transactionEventWithPayload;
import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.nio.charset.StandardCharsets;
import java.util.List;

import com.powerfinance.antifraud.rules.LowHistoryHighValueRule;
import org.junit.jupiter.api.Test;

import com.powerfinance.events.v1.TransactionCreated;

class UndecodablePayloadTest {

    private static final double LOW_HISTORY_HIGH_VALUE_THRESHOLD = 2.0;

    @Test
    void protobufJsonPayloadFromDebeziumIsScored() throws Exception {
        var harness = harnessFor(List.of(new LowHistoryHighValueRule()), LOW_HISTORY_HIGH_VALUE_THRESHOLD);

        harness.processElement(transactionEvent("user_2abc", "5000.00"), 0);

        assertEquals(1, harness.extractOutputValues().size());
        harness.close();
    }

    @Test
    void binaryProtobufPayloadIsSkippedWithoutFailingTheJob() throws Exception {
        var harness = harnessFor(List.of(new LowHistoryHighValueRule()), LOW_HISTORY_HIGH_VALUE_THRESHOLD);
        byte[] binaryPayload = TransactionCreated.newBuilder().setAmount("5000.00").build().toByteArray();

        assertDoesNotThrow(() -> harness.processElement(transactionEventWithPayload("user_2abc", binaryPayload), 0));

        assertTrue(harness.extractOutputValues().isEmpty());
        harness.close();
    }

    @Test
    void emptyPayloadIsSkippedWithoutFailingTheJob() throws Exception {
        var harness = harnessFor(List.of(new LowHistoryHighValueRule()), LOW_HISTORY_HIGH_VALUE_THRESHOLD);

        assertDoesNotThrow(() -> harness.processElement(transactionEventWithPayload("user_2abc", new byte[0]), 0));

        assertTrue(harness.extractOutputValues().isEmpty());
        harness.close();
    }

    @Test
    void nonNumericAmountIsSkippedWithoutFailingTheJob() throws Exception {
        var harness = harnessFor(List.of(new LowHistoryHighValueRule()), LOW_HISTORY_HIGH_VALUE_THRESHOLD);
        byte[] nonNumericAmountPayload = "{\"amount\": \"five thousand\"}".getBytes(StandardCharsets.UTF_8);

        assertDoesNotThrow(() -> harness.processElement(
                transactionEventWithPayload("user_2abc", nonNumericAmountPayload),
                0
        ));

        assertTrue(harness.extractOutputValues().isEmpty());
        harness.close();
    }

    @Test
    void scoringContinuesAfterAnUndecodableEvent() throws Exception {
        var harness = harnessFor(List.of(new LowHistoryHighValueRule()), LOW_HISTORY_HIGH_VALUE_THRESHOLD);

        harness.processElement(transactionEventWithPayload("user_2abc", new byte[] {0x0a, 0x7f}), 0);
        harness.processElement(transactionEvent("user_2abc", "5000.00"), 1);

        assertEquals(1, harness.extractOutputValues().size());
        harness.close();
    }
}
