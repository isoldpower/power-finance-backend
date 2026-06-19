package com.powerfinance.antifraud.rules;

import java.util.List;

import com.google.protobuf.Timestamp;
import com.powerfinance.antifraud.engine.KeyedFraudScoringEngine;
import com.powerfinance.antifraud.model.Alert;
import com.powerfinance.antifraud.model.OutboxEvent;
import org.apache.flink.api.common.typeinfo.Types;
import org.apache.flink.streaming.api.operators.KeyedProcessOperator;
import org.apache.flink.streaming.util.KeyedOneInputStreamOperatorTestHarness;

import com.powerfinance.events.v1.TransactionCreated;

/** Test fixtures for driving fraud rules and the scoring engine through a keyed operator harness. */
public final class RuleTestSupport {

    private RuleTestSupport() {
    }

    /** Builds an open scoring-engine harness around a single rule and threshold. */
    public static KeyedOneInputStreamOperatorTestHarness<String, OutboxEvent, Alert> harnessFor(
            FraudRule fraudRule, double threshold) throws Exception {
        return harnessFor(List.of(fraudRule), threshold);
    }

    /** Builds an open scoring-engine harness around the given rules and threshold. */
    public static KeyedOneInputStreamOperatorTestHarness<String, OutboxEvent, Alert> harnessFor(
            List<FraudRule> fraudRules, double threshold) throws Exception {
        var engine = new KeyedFraudScoringEngine(fraudRules, threshold);
        var harness = new KeyedOneInputStreamOperatorTestHarness<>(
                new KeyedProcessOperator<>(engine),
                OutboxEvent::getClerkId,
                Types.STRING);
        harness.open();
        return harness;
    }

    /** Builds a TransactionCreated outbox event with no event time. */
    public static OutboxEvent transactionEvent(String clerkId, String amount) {
        return transactionEvent(clerkId, amount, 0);
    }

    /** Builds a TransactionCreated outbox event at the given event time in seconds. */
    public static OutboxEvent transactionEvent(String clerkId, String amount, long occurredAtSeconds) {
        var builder = TransactionCreated.newBuilder()
                .setEventId("evt")
                .setTransactionId("txn")
                .setAmount(amount);
        if (occurredAtSeconds > 0) {
            builder.setOccurredAt(Timestamp.newBuilder().setSeconds(occurredAtSeconds).build());
        }
        return new OutboxEvent(clerkId, "TransactionCreated", "evt", builder.build().toByteArray());
    }

    /** Builds a non-transaction outbox event for verifying rules ignore other event types. */
    public static OutboxEvent nonTransactionEvent(String clerkId) {
        return new OutboxEvent(clerkId, "WalletCreated", "evt", new byte[0]);
    }
}
