package com.powerfinance.antifraud.model;

import java.nio.charset.StandardCharsets;

import com.google.protobuf.InvalidProtocolBufferException;
import com.google.protobuf.util.JsonFormat;

import com.powerfinance.events.v1.TransactionCreated;

public final class OutboxPayloads {

    private static final JsonFormat.Parser PROTOBUF_JSON_PARSER = JsonFormat.parser().ignoringUnknownFields();

    private OutboxPayloads() {
    }

    public static TransactionCreated decodeTransactionCreated(byte[] outboxPayload)
            throws InvalidProtocolBufferException {
        if (outboxPayload == null || outboxPayload.length == 0) {
            throw new InvalidProtocolBufferException("outbox payload is empty");
        }

        TransactionCreated.Builder transactionBuilder = TransactionCreated.newBuilder();
        PROTOBUF_JSON_PARSER.merge(new String(outboxPayload, StandardCharsets.UTF_8), transactionBuilder);
        return transactionBuilder.build();
    }
}
