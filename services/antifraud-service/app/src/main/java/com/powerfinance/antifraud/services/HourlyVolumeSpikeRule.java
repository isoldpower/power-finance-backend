package com.powerfinance.antifraud.services;

import java.util.Iterator;
import java.util.Map;

import com.powerfinance.antifraud.types.OutboxEvent;
import org.apache.flink.api.common.functions.RuntimeContext;
import org.apache.flink.api.common.state.MapState;
import org.apache.flink.api.common.state.MapStateDescriptor;

import com.powerfinance.events.v1.TransactionCreated;

public class HourlyVolumeSpikeRule implements FraudRule {

    private static final String EVENT_TYPE = "TransactionCreated";

    private static final long HOUR_MS = 3_600_000L;
    private static final long DAY_MS = 24 * HOUR_MS;
    private static final long WINDOW_24H_BUCKETS = 24;
    private static final long WINDOW_30D_BUCKETS = 24 * 30;

    private static final double MINIMUM_BASELINE_DAYS = 7.0;
    private static final double SPIKE_FACTOR = 3.0;
    private static final double WEIGHT = 4.0;

    private transient MapState<Long, Double> volumeByHourBucketState;

    @Override
    public void open(RuntimeContext runtimeContext) {
        this.volumeByHourBucketState = runtimeContext.getMapState(new MapStateDescriptor<>(
                "volumeByHourBucket",
                Long.class,
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
        long currentHourBucket = eventTimeMillis(transaction) / HOUR_MS;

        recordTransactionVolume(currentHourBucket, transactionAmount);
        WindowVolumes windowVolumes = pruneAndAggregateWindows(currentHourBucket);

        return isVolumeSpike(windowVolumes, currentHourBucket) ? WEIGHT : 0;
    }

    private void recordTransactionVolume(long hourBucket, double transactionAmount) throws Exception {
        Double existingHourVolume = volumeByHourBucketState.get(hourBucket);
        volumeByHourBucketState.put(
                hourBucket,
                (existingHourVolume == null ? 0.0 : existingHourVolume) + transactionAmount
        );
    }

    private WindowVolumes pruneAndAggregateWindows(long currentHourBucket) throws Exception {
        long oldestAllowedBucket = currentHourBucket - WINDOW_30D_BUCKETS + 1;
        long last24hStartBucket = currentHourBucket - WINDOW_24H_BUCKETS + 1;

        double last24hVolume = 0;
        double last30dVolume = 0;
        long earliestBucket = Long.MAX_VALUE;

        Iterator<Map.Entry<Long, Double>> bucketIterator = volumeByHourBucketState.iterator();
        while (bucketIterator.hasNext()) {
            Map.Entry<Long, Double> hourBucket = bucketIterator.next();
            long bucket = hourBucket.getKey();
            if (bucket < oldestAllowedBucket) {
                bucketIterator.remove();
                continue;
            }

            double bucketVolume = hourBucket.getValue();
            last30dVolume += bucketVolume;
            if (bucket >= last24hStartBucket) {
                last24hVolume += bucketVolume;
            } else {
                earliestBucket = Math.min(earliestBucket, bucket);
            }
        }

        return new WindowVolumes(last24hVolume, last30dVolume, earliestBucket);
    }

    private boolean isVolumeSpike(WindowVolumes windowVolumes, long currentHourBucket) {
        long last24hStartBucket = currentHourBucket - WINDOW_24H_BUCKETS + 1;
        long baselineSpanBuckets = last24hStartBucket - windowVolumes.earliestBucket();
        double baselineDays = baselineSpanBuckets * (double) HOUR_MS / DAY_MS;
        if (baselineDays < MINIMUM_BASELINE_DAYS) {
            return false;
        }

        double baselineVolume = windowVolumes.last30dVolume() - windowVolumes.last24hVolume();
        double baselineDailyAverage = baselineVolume / baselineDays;

        return (
                baselineDailyAverage > 0 &&
                windowVolumes.last24hVolume() > SPIKE_FACTOR * baselineDailyAverage
        );
    }

    private static long eventTimeMillis(TransactionCreated transaction) {
        long occurredAtSeconds = transaction.getOccurredAt().getSeconds();
        if (occurredAtSeconds == 0) {
            return System.currentTimeMillis();
        }

        return occurredAtSeconds * 1000 + transaction.getOccurredAt().getNanos() / 1_000_000;
    }

    private record WindowVolumes(double last24hVolume, double last30dVolume, long earliestBucket) { }
}
