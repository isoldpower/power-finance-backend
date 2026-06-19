package com.powerfinance.antifraud.io;

import java.nio.charset.StandardCharsets;

import com.powerfinance.antifraud.model.OutboxEvent;
import org.apache.flink.api.common.typeinfo.TypeInformation;
import org.apache.flink.util.Collector;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.apache.kafka.common.header.Header;

/** Decodes outbox Kafka records into outbox events, dropping any missing required headers. */
public class KafkaOutboxDecoder implements InflowDecoder {
    private static final String HEADER_EVENT_ID = "event_id";
    private static final String HEADER_EVENT_TYPE = "event_type";

    /** Emits an outbox event built from the record key, headers and value when both headers are present. */
    @Override
    public void deserialize(ConsumerRecord<byte[], byte[]> consumerRecord, Collector<OutboxEvent> decodedEvents) {
        String eventType = header(consumerRecord, HEADER_EVENT_TYPE);
        String eventId = header(consumerRecord, HEADER_EVENT_ID);
        if (eventType == null || eventId == null) {
            return;
        }

        String clerkId = consumerRecord.key() == null
                ? ""
                : new String(consumerRecord.key(), StandardCharsets.UTF_8);
        decodedEvents.collect(new OutboxEvent(clerkId, eventType, eventId, consumerRecord.value()));
    }

    /** Reports the produced type so Flink can infer serialization for the decoded events. */
    @Override
    public TypeInformation<OutboxEvent> getProducedType() {
        return TypeInformation.of(OutboxEvent.class);
    }

    private static String header(ConsumerRecord<byte[], byte[]> consumerRecord, String headerName) {
        Header header = consumerRecord.headers().lastHeader(headerName);
        return header == null ? null : new String(header.value(), StandardCharsets.UTF_8);
    }
}
