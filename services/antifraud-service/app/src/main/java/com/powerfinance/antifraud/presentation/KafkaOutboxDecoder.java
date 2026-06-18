package com.powerfinance.antifraud.presentation;

import com.powerfinance.antifraud.types.OutboxEvent;
import org.apache.flink.api.common.typeinfo.TypeInformation;
import org.apache.flink.util.Collector;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.apache.kafka.common.header.Header;

import java.nio.charset.StandardCharsets;


public class KafkaOutboxDecoder implements InflowDecoder {
    private static final String HEADER_EVENT_ID = "event_id";
    private static final String HEADER_EVENT_TYPE = "event_type";

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

    @Override
    public TypeInformation<OutboxEvent> getProducedType() {
        return TypeInformation.of(OutboxEvent.class);
    }

    private static String header(ConsumerRecord<byte[], byte[]> consumerRecord, String headerName) {
        Header header = consumerRecord.headers().lastHeader(headerName);
        return header == null ? null : new String(header.value(), StandardCharsets.UTF_8);
    }
}
