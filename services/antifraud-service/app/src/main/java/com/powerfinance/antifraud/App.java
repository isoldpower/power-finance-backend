package com.powerfinance.antifraud;

import java.util.List;

import com.powerfinance.antifraud.config.AntifraudConfig;
import com.powerfinance.antifraud.presentation.InflowSource;
import com.powerfinance.antifraud.presentation.KafkaOutboxSource;
import com.powerfinance.antifraud.services.AmountDeviationRule;
import com.powerfinance.antifraud.services.FraudRule;
import com.powerfinance.antifraud.services.FraudScoringEngine;
import com.powerfinance.antifraud.services.HourlyVolumeSpikeRule;
import com.powerfinance.antifraud.services.LowHistoryHighValueRule;
import org.apache.flink.streaming.api.environment.StreamExecutionEnvironment;


public class App {

    public static void main(String[] args) throws Exception {
        AntifraudConfig config = AntifraudConfig.fromEnvironment();
        var executionEnvironment = StreamExecutionEnvironment.getExecutionEnvironment();

        List<FraudRule> fraudRules = List.of(
                new AmountDeviationRule(),
                new LowHistoryHighValueRule(),
                new HourlyVolumeSpikeRule()
        );
        var fraudScoringEngine = new FraudScoringEngine(fraudRules, config.fraudScoreThreshold());

        List<InflowSource> inflowSources = List.of(new KafkaOutboxSource(
                config.kafkaBootstrapServers(),
                config.kafkaOutboxTopic(),
                config.kafkaGroupId(),
                fraudScoringEngine
        ));

        for (InflowSource inflowSource : inflowSources) {
            inflowSource.bindEnvironment(executionEnvironment);
        }

        executionEnvironment.execute("fraud-detection");
    }
}
