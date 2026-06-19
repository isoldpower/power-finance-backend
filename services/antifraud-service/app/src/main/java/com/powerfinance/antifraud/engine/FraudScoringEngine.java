package com.powerfinance.antifraud.engine;

import com.powerfinance.antifraud.model.Alert;
import com.powerfinance.antifraud.model.OutboxEvent;
import org.apache.flink.streaming.api.datastream.DataStream;

/** Scoring layer contract that turns a stream of outbox events into a stream of fraud alerts. */
public interface FraudScoringEngine {

    /** Scores the events and returns the alerts whose score exceeds the fraud threshold. */
    DataStream<Alert> score(DataStream<OutboxEvent> events);
}
