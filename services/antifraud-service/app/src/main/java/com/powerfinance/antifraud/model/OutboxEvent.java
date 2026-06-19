package com.powerfinance.antifraud.model;

/** Decoded outbox record consumed from Kafka, carried as a Flink POJO through scoring. */
public class OutboxEvent {
    private String clerkId;
    private String eventType;
    private String eventId;
    private byte[] payload;

    public OutboxEvent() {}

    public OutboxEvent(String clerkId, String eventType, String eventId, byte[] payload) {
        this.clerkId = clerkId;
        this.eventType = eventType;
        this.eventId = eventId;
        this.payload = payload;
    }

    /** Returns the Clerk id the event is keyed by. */
    public String getClerkId() {
        return clerkId;
    }

    /** Sets the Clerk id the event is keyed by. */
    public void setClerkId(String clerkId) {
        this.clerkId = clerkId;
    }

    /** Returns the event type discriminator. */
    public String getEventType() {
        return eventType;
    }

    /** Sets the event type discriminator. */
    public void setEventType(String eventType) {
        this.eventType = eventType;
    }

    /** Returns the unique event id. */
    public String getEventId() {
        return eventId;
    }

    /** Sets the unique event id. */
    public void setEventId(String eventId) {
        this.eventId = eventId;
    }

    /** Returns the raw protobuf payload bytes. */
    public byte[] getPayload() {
        return payload;
    }

    /** Sets the raw protobuf payload bytes. */
    public void setPayload(byte[] payload) {
        this.payload = payload;
    }
}
