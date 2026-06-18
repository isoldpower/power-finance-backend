package com.powerfinance.antifraud.services;

import com.powerfinance.antifraud.types.OutboxEvent;
import org.apache.flink.api.common.functions.RuntimeContext;
import org.apache.flink.api.common.state.ValueState;
import org.apache.flink.api.common.state.ValueStateDescriptor;

import com.powerfinance.events.v1.TransactionCreated;

public class LowHistoryHighValueRule implements FraudRule {

    private static final String EVENT_TYPE = "TransactionCreated";
    private static final double SMALL_HISTORY_THRESHOLD = 100.0;
    private static final double LARGE_TRANSACTION_THRESHOLD = 1000.0;
    private static final double WEIGHT = 3.0;

    private transient ValueState<Double> transactionTotalState;

    @Override
    public void open(RuntimeContext runtimeContext) {
        this.transactionTotalState = runtimeContext.getState(new ValueStateDescriptor<>(
                "transactionTotal",
                Double.class
        ));
    }

    @Override
    public double score(OutboxEvent outboxEvent) throws Exception {
        if (!EVENT_TYPE.equals(outboxEvent.eventType)) {
            return 0;
        }

        TransactionCreated transaction = TransactionCreated.parseFrom(outboxEvent.payload);
        double transactionAmount = Double.parseDouble(transaction.getAmount());

        Double priorTransactionTotal = transactionTotalState.value();
        if (priorTransactionTotal == null) {
            priorTransactionTotal = 0.0;
        }

        double rulePoints = 0;
        boolean historyIsThin = priorTransactionTotal < SMALL_HISTORY_THRESHOLD;
        boolean transactionIsLarge = transactionAmount > LARGE_TRANSACTION_THRESHOLD;
        if (historyIsThin && transactionIsLarge) {
            rulePoints = WEIGHT;
        }

        transactionTotalState.update(priorTransactionTotal + transactionAmount);
        return rulePoints;
    }
}
