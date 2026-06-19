package com.powerfinance.antifraud.io;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;

import com.powerfinance.antifraud.model.OutboxEvent;
import org.apache.flink.util.Collector;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.junit.jupiter.api.Test;

import com.powerfinance.events.v1.TransactionCreated;

class KafkaOutboxDecoderTest {

    private final KafkaOutboxDecoder outboxDecoder = new KafkaOutboxDecoder();

    @Test
    void decodesEnvelopeAndPreservesProtoPayload() throws Exception {
        TransactionCreated transaction = TransactionCreated.newBuilder()
                .setEventId("evt-1")
                .setTransactionId("txn-1")
                .setUserId(42)
                .setAmount("12345.67")
                .build();

        var consumerRecord =
                recordWith("clerk_abc", "TransactionCreated", "evt-1", transaction.toByteArray());
        var decodedEvents = collect(consumerRecord);

        assertEquals(1, decodedEvents.size());
        OutboxEvent decodedEvent = decodedEvents.get(0);
        assertEquals("clerk_abc", decodedEvent.getClerkId());
        assertEquals("TransactionCreated", decodedEvent.getEventType());
        assertEquals("evt-1", decodedEvent.getEventId());
        assertEquals(transaction, TransactionCreated.parseFrom(decodedEvent.getPayload()));
    }

    @Test
    void dropsRecordMissingRequiredHeaders() {
        var consumerRecord = recordWith("clerk_abc", null, null, new byte[0]);
        assertTrue(collect(consumerRecord).isEmpty());
    }

    @Test
    void emptyKeyBecomesEmptyClerkId() {
        var consumerRecord =
                new ConsumerRecord<byte[], byte[]>("events.async", 0, 0L, null, new byte[0]);
        consumerRecord.headers().add("event_id", "evt-1".getBytes(StandardCharsets.UTF_8));
        consumerRecord.headers().add("event_type", "TransactionCreated".getBytes(StandardCharsets.UTF_8));

        var decodedEvents = collect(consumerRecord);
        assertEquals(1, decodedEvents.size());
        assertEquals("", decodedEvents.get(0).getClerkId());
        assertNull(consumerRecord.key());
    }

    private static ConsumerRecord<byte[], byte[]> recordWith(
            String key, String eventType, String eventId, byte[] value) {
        var consumerRecord = new ConsumerRecord<byte[], byte[]>(
                "events.async", 0, 0L, key.getBytes(StandardCharsets.UTF_8), value);
        if (eventId != null) {
            consumerRecord.headers().add("event_id", eventId.getBytes(StandardCharsets.UTF_8));
        }
        if (eventType != null) {
            consumerRecord.headers().add("event_type", eventType.getBytes(StandardCharsets.UTF_8));
        }
        return consumerRecord;
    }

    private List<OutboxEvent> collect(ConsumerRecord<byte[], byte[]> consumerRecord) {
        List<OutboxEvent> decodedEvents = new ArrayList<>();
        outboxDecoder.deserialize(consumerRecord, new Collector<>() {
            @Override
            public void collect(OutboxEvent decodedEvent) {
                decodedEvents.add(decodedEvent);
            }

            @Override
            public void close() {}
        });
        return decodedEvents;
    }
}
