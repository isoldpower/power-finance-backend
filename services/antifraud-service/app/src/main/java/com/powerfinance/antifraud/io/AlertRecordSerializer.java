package com.powerfinance.antifraud.io;

import java.nio.charset.StandardCharsets;

import com.powerfinance.antifraud.model.Alert;
import org.apache.flink.connector.kafka.sink.KafkaRecordSerializationSchema;
import org.apache.kafka.clients.producer.ProducerRecord;

/** Serializes a fraud alert into a Kafka record keyed by the user's clerk id. */
public class AlertRecordSerializer implements KafkaRecordSerializationSchema<Alert> {
    private final String topic;

    public AlertRecordSerializer(String topic) {
        this.topic = topic;
    }

    /** Builds a producer record carrying the clerk id as key and the message as value. */
    @Override
    public ProducerRecord<byte[], byte[]> serialize(
            Alert alert, KafkaSinkContext context, Long timestamp) {
        return new ProducerRecord<>(
                topic,
                alert.getClerkId().getBytes(StandardCharsets.UTF_8),
                alert.getMessage().getBytes(StandardCharsets.UTF_8));
    }
}
