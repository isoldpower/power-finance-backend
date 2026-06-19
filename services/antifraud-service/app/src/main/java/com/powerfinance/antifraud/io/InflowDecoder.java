package com.powerfinance.antifraud.io;

import com.powerfinance.antifraud.model.OutboxEvent;
import org.apache.flink.connector.kafka.source.reader.deserializer.KafkaRecordDeserializationSchema;

/** Kafka deserialization schema that decodes inbound records into outbox events. */
public interface InflowDecoder extends KafkaRecordDeserializationSchema<OutboxEvent> {
}
