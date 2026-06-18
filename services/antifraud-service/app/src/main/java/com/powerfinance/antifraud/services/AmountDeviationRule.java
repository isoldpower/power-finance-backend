package com.powerfinance.antifraud.services;

import com.powerfinance.antifraud.types.OutboxEvent;
import org.apache.flink.api.common.functions.RuntimeContext;
import org.apache.flink.api.common.state.ValueState;
import org.apache.flink.api.common.state.ValueStateDescriptor;

import com.powerfinance.events.v1.TransactionCreated;

public class AmountDeviationRule implements FraudRule {

    private static final String EVENT_TYPE = "TransactionCreated";
    private static final double SIGMA_THRESHOLD = 3.0;
    private static final long MINIMUM_SAMPLE_COUNT = 30;
    private static final double OUTLIER_WEIGHT = 5.0;

    private transient ValueState<RunningStats> amountStatsState;

    @Override
    public void open(RuntimeContext runtimeContext) {
        this.amountStatsState = runtimeContext.getState(new ValueStateDescriptor<>(
                "amountStats",
                RunningStats.class
        ));
    }

    @Override
    public double score(OutboxEvent outboxEvent) throws Exception {
        if (!EVENT_TYPE.equals(outboxEvent.eventType)) {
            return 0;
        }

        TransactionCreated transaction = TransactionCreated.parseFrom(outboxEvent.payload);
        double transactionAmount = Double.parseDouble(transaction.getAmount());

        RunningStats runningAmountStats = amountStatsState.value();
        if (runningAmountStats == null) {
            runningAmountStats = new RunningStats();
        }

        double rulePoints = 0;
        if (runningAmountStats.count >= MINIMUM_SAMPLE_COUNT) {
            double standardDeviation = Math.sqrt(runningAmountStats.m2 / (runningAmountStats.count - 1));
            double amountDeviation = Math.abs(transactionAmount - runningAmountStats.mean);
            if (standardDeviation > 0 && amountDeviation > SIGMA_THRESHOLD * standardDeviation) {
                rulePoints = OUTLIER_WEIGHT;
            }
        }

        runningAmountStats.add(transactionAmount);
        amountStatsState.update(runningAmountStats);
        return rulePoints;
    }

    static class RunningStats {
        public long count;
        public double mean;
        public double m2;

        public void add(double value) {
            count += 1;
            double delta = value - mean;
            mean += delta / count;
            double delta2 = value - mean;
            m2 += delta * delta2;
        }
    }
}
