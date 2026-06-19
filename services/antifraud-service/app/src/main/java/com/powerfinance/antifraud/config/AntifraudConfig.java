package com.powerfinance.antifraud.config;

/** Immutable runtime configuration for the antifraud Flink job. */
public record AntifraudConfig(
        String kafkaBootstrapServers,
        String kafkaOutboxTopic,
        String kafkaGroupId,
        String kafkaAlertsTopic,
        double fraudScoreThreshold
) {

    /** Builds the configuration from environment variables, falling back to defaults. */
    public static AntifraudConfig fromEnvironment() {
        return new AntifraudConfig(
                environmentValue("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
                environmentValue("KAFKA_OUTBOX_TOPIC", "events.async"),
                environmentValue("KAFKA_GROUP_ID", "antifraud-service"),
                environmentValue("KAFKA_ALERTS_TOPIC", "fraud.alerts"),
                Double.parseDouble(environmentValue("FRAUD_SCORE_THRESHOLD", "4.0"))
        );
    }

    private static String environmentValue(String name, String fallback) {
        String value = System.getenv(name);
        return value == null || value.isBlank() ? fallback : value;
    }
}
