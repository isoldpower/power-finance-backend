package com.powerfinance.antifraud.presentation;

import com.powerfinance.antifraud.types.Alert;
import com.powerfinance.antifraud.types.OutboxEvent;
import org.apache.flink.api.common.eventtime.WatermarkStrategy;
import org.apache.flink.connector.base.DeliveryGuarantee;
import org.apache.flink.connector.kafka.sink.KafkaSink;
import org.apache.flink.connector.kafka.source.KafkaSource;
import org.apache.flink.connector.kafka.source.enumerator.initializer.OffsetsInitializer;
import org.apache.flink.streaming.api.environment.StreamExecutionEnvironment;
import org.apache.flink.streaming.api.functions.KeyedProcessFunction;


public class KafkaOutboxSource implements InflowSource {
    private final String topic;
    private final KafkaSource<OutboxEvent> outboxKafkaSource;
    private final KafkaSink<Alert> alertsKafkaSink;
    private final KeyedProcessFunction<String, OutboxEvent, Alert> fraudScoringProcessor;

    public KafkaOutboxSource(
            String bootstrapServers,
            String topic,
            String groupId,
            String alertsTopic,
            KeyedProcessFunction<String, OutboxEvent, Alert> fraudScoringProcessor) {
        this.topic = topic;
        this.fraudScoringProcessor = fraudScoringProcessor;
        this.outboxKafkaSource = KafkaSource.<OutboxEvent>builder()
                .setBootstrapServers(bootstrapServers)
                .setTopics(topic)
                .setGroupId(groupId)
                .setStartingOffsets(OffsetsInitializer.latest())
                .setDeserializer(new KafkaOutboxDecoder())
                .build();
        this.alertsKafkaSink = KafkaSink.<Alert>builder()
                .setBootstrapServers(bootstrapServers)
                .setRecordSerializer(new AlertRecordSerializer(alertsTopic))
                .setDeliveryGuarantee(DeliveryGuarantee.AT_LEAST_ONCE)
                .build();
    }

    public void bindEnvironment(StreamExecutionEnvironment executionEnvironment) {
        var fraudAlerts = executionEnvironment
                .fromSource(this.outboxKafkaSource, WatermarkStrategy.noWatermarks(), this.topic)
                .keyBy((outboxEvent) -> outboxEvent.clerkId)
                .process(this.fraudScoringProcessor);

        fraudAlerts.sinkTo(this.alertsKafkaSink);
        fraudAlerts.print();
    }
}
