package com.powerfinance.antifraud;

import java.util.List;

import com.powerfinance.antifraud.config.AntifraudConfig;
import com.powerfinance.antifraud.engine.FraudScoringEngine;
import com.powerfinance.antifraud.engine.KeyedFraudScoringEngine;
import com.powerfinance.antifraud.io.InflowSource;
import com.powerfinance.antifraud.io.KafkaOutboxSource;
import com.powerfinance.antifraud.rules.AmountDeviationRule;
import com.powerfinance.antifraud.rules.FraudRule;
import com.powerfinance.antifraud.rules.HourlyVolumeSpikeRule;
import com.powerfinance.antifraud.rules.LowHistoryHighValueRule;
import org.apache.flink.streaming.api.environment.StreamExecutionEnvironment;

/** Entry point that assembles the fraud rules, scoring engine and Kafka inflow into a Flink job. */
public class App {

    /** Builds the scoring pipeline from environment config and executes the Flink job. */
    public static void main(String[] args) throws Exception {
        AntifraudConfig config = AntifraudConfig.fromEnvironment();
        var executionEnvironment = StreamExecutionEnvironment.getExecutionEnvironment();

        List<FraudRule> fraudRules = List.of(
                new AmountDeviationRule(),
                new LowHistoryHighValueRule(),
                new HourlyVolumeSpikeRule()
        );
        FraudScoringEngine fraudScoringEngine =
                new KeyedFraudScoringEngine(fraudRules, config.fraudScoreThreshold());

        List<InflowSource> inflowSources = List.of(new KafkaOutboxSource(
                config.kafkaBootstrapServers(),
                config.kafkaOutboxTopic(),
                config.kafkaGroupId(),
                config.kafkaAlertsTopic(),
                fraudScoringEngine
        ));

        for (InflowSource inflowSource : inflowSources) {
            inflowSource.bindEnvironment(executionEnvironment);
        }

        executionEnvironment.execute("fraud-detection");
    }
}
