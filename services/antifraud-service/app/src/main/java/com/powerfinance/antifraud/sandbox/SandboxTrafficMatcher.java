package com.powerfinance.antifraud.sandbox;

import java.io.Serializable;

public final class SandboxTrafficMatcher implements Serializable {
    private static final long serialVersionUID = 1L;

    private final String ownSandboxId;

    public SandboxTrafficMatcher(String ownSandboxId) {
        this.ownSandboxId = ownSandboxId == null ? "" : ownSandboxId;
    }

    public static SandboxTrafficMatcher fromEnvironment() {
        return new SandboxTrafficMatcher(SandboxIdentity.resolveOwnId());
    }

    public String ownSandboxId() {
        return this.ownSandboxId;
    }

    public boolean isBaseline() {
        return this.ownSandboxId.isEmpty();
    }

    public boolean isOwnedTraffic(String messageSandboxId) {
        String normalizedMessageSandboxId = messageSandboxId == null ? "" : messageSandboxId;

        return normalizedMessageSandboxId.equals(this.ownSandboxId);
    }
}
