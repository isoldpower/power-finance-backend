"""Baseline consumers own untagged traffic; sandbox consumers own only their own."""

from observability import SandboxTrafficMatcher
from observability.sandbox import ENVIRONMENT_VARIABLE_SANDBOX_ID


def test_baseline_matcher_owns_untagged_traffic_only():
    matcher = SandboxTrafficMatcher(None)

    assert matcher.is_baseline
    assert matcher.is_owned_traffic(None)
    assert not matcher.is_owned_traffic("nikita")


def test_sandbox_matcher_owns_its_own_traffic_only():
    matcher = SandboxTrafficMatcher("nikita")

    assert not matcher.is_baseline
    assert matcher.is_owned_traffic("nikita")
    assert not matcher.is_owned_traffic(None)
    assert not matcher.is_owned_traffic("someone-else")


def test_matcher_from_environment_reads_sandbox_id(monkeypatch):
    monkeypatch.setenv(ENVIRONMENT_VARIABLE_SANDBOX_ID, "nikita")

    assert SandboxTrafficMatcher.from_environment().own_sandbox_id == "nikita"


def test_matcher_from_environment_treats_blank_as_baseline(monkeypatch):
    monkeypatch.setenv(ENVIRONMENT_VARIABLE_SANDBOX_ID, "   ")

    assert SandboxTrafficMatcher.from_environment().is_baseline
