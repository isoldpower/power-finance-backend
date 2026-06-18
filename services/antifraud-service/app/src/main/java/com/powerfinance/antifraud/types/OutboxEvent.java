package com.powerfinance.antifraud.types;

public class OutboxEvent {
    public String clerkId;
    public String eventType;
    public String eventId;
    public byte[] payload;

    public OutboxEvent() {}

    public OutboxEvent(String clerkId, String eventType, String eventId, byte[] payload) {
        this.clerkId = clerkId;
        this.eventType = eventType;
        this.eventId = eventId;
        this.payload = payload;
    }
}
