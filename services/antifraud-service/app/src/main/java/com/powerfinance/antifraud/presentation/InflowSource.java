package com.powerfinance.antifraud.presentation;

import org.apache.flink.streaming.api.environment.StreamExecutionEnvironment;


public interface InflowSource {
    void bindEnvironment(StreamExecutionEnvironment executionEnvironment);
}
