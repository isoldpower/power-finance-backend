package com.powerfinance.antifraud.services;

import java.util.List;

import com.google.protobuf.Timestamp;
import com.powerfinance.antifraud.types.OutboxEvent;
import org.apache.flink.api.common.typeinfo.Types;
import org.apache.flink.streaming.api.operators.KeyedProcessOperator;
import org.apache.flink.streaming.util.KeyedOneInputStreamOperatorTestHarness;

import com.powerfinance.events.v1.TransactionCreated;

final class RuleTestSupport {

    private RuleTestSupport() {
    }

    static KeyedOneInputStreamOperatorTestHarness<String, OutboxEvent, String> harnessFor(
            FraudRule fraudRule, double threshold) throws Exception {
        return harnessFor(List.of(fraudRule), threshold);
    }

    static KeyedOneInputStreamOperatorTestHarness<String, OutboxEvent, String> harnessFor(
            List<FraudRule> fraudRules, double threshold) throws Exception {
        var engine = new FraudScoringEngine(fraudRules, threshold);
        var harness = new KeyedOneInputStreamOperatorTestHarness<>(
                new KeyedProcessOperator<>(engine),
                (OutboxEvent outboxEvent) -> outboxEvent.clerkId,
                Types.STRING);
        harness.open();
        return harness;
    }

    static OutboxEvent transactionEvent(String clerkId, String amount) {
        return transactionEvent(clerkId, amount, 0);
    }

    static OutboxEvent transactionEvent(String clerkId, String amount, long occurredAtSeconds) {
        var builder = TransactionCreated.newBuilder()
                .setEventId("evt")
                .setTransactionId("txn")
                .setAmount(amount);
        if (occurredAtSeconds > 0) {
            builder.setOccurredAt(Timestamp.newBuilder().setSeconds(occurredAtSeconds).build());
        }
        return new OutboxEvent(clerkId, "TransactionCreated", "evt", builder.build().toByteArray());
    }

    static OutboxEvent nonTransactionEvent(String clerkId) {
        return new OutboxEvent(clerkId, "WalletCreated", "evt", new byte[0]);
    }
}
