package com.powerfinance.antifraud.rules;

import java.io.Serializable;

import com.powerfinance.antifraud.model.OutboxEvent;
import org.apache.flink.api.common.functions.RuntimeContext;

/** A single fraud heuristic that contributes a weighted score for an event. */
public interface FraudRule extends Serializable {

    /** Initialises any keyed state the rule needs from the Flink runtime context. */
    void open(RuntimeContext runtimeContext) throws Exception;

    /** Returns this rule's fraud points for the event, or zero when it does not apply. */
    double score(OutboxEvent outboxEvent) throws Exception;
}
