package com.powerfinance.antifraud.sandbox;

public final class SandboxIdentity {
    public static final String BAGGAGE_HEADER_NAME = "baggage";
    public static final String BAGGAGE_ENTRY_NAME = "sandbox-id";
    public static final String ENVIRONMENT_VARIABLE_SANDBOX_ID = "SANDBOX_ID";
    public static final String GROUP_ID_SEPARATOR = "-sbx-";

    private SandboxIdentity() {
    }

    public static String resolveOwnId() {
        String configuredSandboxId = System.getenv(ENVIRONMENT_VARIABLE_SANDBOX_ID);
        if (configuredSandboxId == null || configuredSandboxId.isBlank()) {
            return "";
        }

        return configuredSandboxId.strip();
    }

    public static String scopeGroupId(String groupId, String sandboxId) {
        if (sandboxId == null || sandboxId.isBlank()) {
            return groupId;
        }

        return groupId + GROUP_ID_SEPARATOR + sandboxId;
    }

    public static String readBaggageEntry(String baggageHeaderValue, String entryName) {
        if (baggageHeaderValue == null || baggageHeaderValue.isBlank()) {
            return "";
        }

        for (String rawEntry : baggageHeaderValue.split(",")) {
            int separatorIndex = rawEntry.indexOf('=');
            if (separatorIndex < 0) {
                continue;
            }
            if (!rawEntry.substring(0, separatorIndex).strip().equals(entryName)) {
                continue;
            }

            String entryValue = rawEntry.substring(separatorIndex + 1);
            int propertyIndex = entryValue.indexOf(';');
            if (propertyIndex >= 0) {
                entryValue = entryValue.substring(0, propertyIndex);
            }

            return entryValue.strip();
        }

        return "";
    }
}
