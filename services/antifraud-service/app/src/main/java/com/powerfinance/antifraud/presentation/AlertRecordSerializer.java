package com.powerfinance.antifraud.presentation;

import java.nio.charset.StandardCharsets;

import com.powerfinance.antifraud.types.Alert;
import org.apache.flink.connector.kafka.sink.KafkaRecordSerializationSchema;
import org.apache.kafka.clients.producer.ProducerRecord;


public class AlertRecordSerializer implements KafkaRecordSerializationSchema<Alert> {
    private final String topic;

    public AlertRecordSerializer(String topic) {
        this.topic = topic;
    }

    @Override
    public ProducerRecord<byte[], byte[]> serialize(
            Alert alert, KafkaSinkContext context, Long timestamp) {
        return new ProducerRecord<>(
                topic,
                alert.clerkId.getBytes(StandardCharsets.UTF_8),
                alert.message.getBytes(StandardCharsets.UTF_8));
    }
}
