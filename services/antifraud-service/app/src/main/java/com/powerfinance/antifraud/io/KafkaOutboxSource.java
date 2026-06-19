package com.powerfinance.antifraud.io;

import com.powerfinance.antifraud.engine.FraudScoringEngine;
import com.powerfinance.antifraud.model.Alert;
import com.powerfinance.antifraud.model.OutboxEvent;
import org.apache.flink.api.common.eventtime.WatermarkStrategy;
import org.apache.flink.connector.base.DeliveryGuarantee;
import org.apache.flink.connector.kafka.sink.KafkaSink;
import org.apache.flink.connector.kafka.source.KafkaSource;
import org.apache.flink.connector.kafka.source.enumerator.initializer.OffsetsInitializer;
import org.apache.flink.streaming.api.datastream.DataStream;
import org.apache.flink.streaming.api.environment.StreamExecutionEnvironment;

/** Inflow source that reads the outbox topic, delegates scoring to the engine and sinks alerts to Kafka. */
public class KafkaOutboxSource implements InflowSource {
    private final String topic;
    private final KafkaSource<OutboxEvent> outboxKafkaSource;
    private final KafkaSink<Alert> alertsKafkaSink;
    private final FraudScoringEngine fraudScoringEngine;

    public KafkaOutboxSource(
            String bootstrapServers,
            String topic,
            String groupId,
            String alertsTopic,
            FraudScoringEngine fraudScoringEngine) {
        this.topic = topic;
        this.fraudScoringEngine = fraudScoringEngine;
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

    /** Reads the outbox topic, scores it through the engine and wires the alerts into the sink. */
    @Override
    public void bindEnvironment(StreamExecutionEnvironment executionEnvironment) {
        DataStream<OutboxEvent> outboxEvents = executionEnvironment
                .fromSource(this.outboxKafkaSource, WatermarkStrategy.noWatermarks(), this.topic);
        DataStream<Alert> fraudAlerts = this.fraudScoringEngine.score(outboxEvents);

        fraudAlerts.sinkTo(this.alertsKafkaSink);
        fraudAlerts.print();
    }
}
