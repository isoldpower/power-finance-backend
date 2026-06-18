package com.powerfinance.antifraud.services;

import java.io.Serializable;

import com.powerfinance.antifraud.types.OutboxEvent;
import org.apache.flink.api.common.functions.RuntimeContext;

public interface FraudRule extends Serializable {

    void open(RuntimeContext runtimeContext) throws Exception;

    double score(OutboxEvent outboxEvent) throws Exception;
}
