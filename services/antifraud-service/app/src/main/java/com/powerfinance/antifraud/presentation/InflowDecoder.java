package com.powerfinance.antifraud.presentation;

import com.powerfinance.antifraud.types.OutboxEvent;
import org.apache.flink.connector.kafka.source.reader.deserializer.KafkaRecordDeserializationSchema;


public interface InflowDecoder extends KafkaRecordDeserializationSchema<OutboxEvent> {
}
