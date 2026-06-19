package com.powerfinance.antifraud.io;

import org.apache.flink.streaming.api.environment.StreamExecutionEnvironment;

/** A data inflow that wires its source, scoring and sink into a Flink execution environment. */
public interface InflowSource {

    /** Attaches this source's processing pipeline to the given execution environment. */
    void bindEnvironment(StreamExecutionEnvironment executionEnvironment);
}
