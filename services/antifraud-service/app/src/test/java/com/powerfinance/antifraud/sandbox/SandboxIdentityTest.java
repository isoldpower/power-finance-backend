package com.powerfinance.antifraud.sandbox;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

class SandboxIdentityTest {

    @Test
    void baselineGroupIdIsLeftUntouched() {
        assertEquals("antifraud-service", SandboxIdentity.scopeGroupId("antifraud-service", ""));
        assertEquals("antifraud-service", SandboxIdentity.scopeGroupId("antifraud-service", null));
    }

    @Test
    void sandboxGroupIdIsSuffixed() {
        assertEquals(
                "antifraud-service-sbx-nikita",
                SandboxIdentity.scopeGroupId("antifraud-service", "nikita")
        );
    }

    @Test
    void sandboxIdIsReadFromBaggage() {
        assertEquals(
                "nikita",
                SandboxIdentity.readBaggageEntry("request-id=abc,sandbox-id=nikita", "sandbox-id")
        );
    }

    @Test
    void entryPropertiesAreStripped() {
        assertEquals(
                "nikita",
                SandboxIdentity.readBaggageEntry("sandbox-id=nikita;meta=1", "sandbox-id")
        );
    }

    @Test
    void missingBaggageYieldsEmptySandboxId() {
        assertEquals("", SandboxIdentity.readBaggageEntry(null, "sandbox-id"));
        assertEquals("", SandboxIdentity.readBaggageEntry("request-id=abc", "sandbox-id"));
    }

    @Test
    void baselineMatcherOwnsUntaggedTrafficOnly() {
        SandboxTrafficMatcher matcher = new SandboxTrafficMatcher("");

        assertTrue(matcher.isBaseline());
        assertTrue(matcher.isOwnedTraffic(""));
        assertTrue(matcher.isOwnedTraffic(null));
        assertFalse(matcher.isOwnedTraffic("nikita"));
    }

    @Test
    void sandboxMatcherOwnsItsOwnTrafficOnly() {
        SandboxTrafficMatcher matcher = new SandboxTrafficMatcher("nikita");

        assertFalse(matcher.isBaseline());
        assertTrue(matcher.isOwnedTraffic("nikita"));
        assertFalse(matcher.isOwnedTraffic(""));
        assertFalse(matcher.isOwnedTraffic("someone-else"));
    }
}
