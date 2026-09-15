"""A consumer's group id must be the same wherever it is written down.

The baseline decides whether a sandbox owns an event by naming the group its own
counterpart would use — `<own-group>-sbx-<sandbox>` — and checking whether it exists.
So a process that joins a different group than the one the baseline derives is
invisible: the baseline processes the sandbox's events, the sandbox processes them
too, and both write to the same datastore. Deltas do not survive that twice.

The gap is not hypothetical. read-service's settings defaulted to
`read-service.test-consumer` while its compose passed `read-service.write-consumer`,
which was harmless until group names became load-bearing — and it only showed up when
a developer ran the consumer on a laptop, where compose is not there to supply it.
"""

import pytest

from ..consumer_groups import (
    ENVIRONMENT_SOURCES,
    GROUP_ID_SOURCES,
    compose_default,
    environment_value,
    generator_pin,
    settings_default,
)


@pytest.mark.parametrize("variable", sorted(GROUP_ID_SOURCES))
def test_the_code_default_matches_what_compose_passes(variable):
    settings_path, compose_path = GROUP_ID_SOURCES[variable]

    assert settings_default(variable, settings_path) == compose_default(variable, compose_path)


@pytest.mark.parametrize("variable", sorted(ENVIRONMENT_SOURCES))
def test_the_env_template_matches_what_compose_passes(variable):
    template_path, compose_path = ENVIRONMENT_SOURCES[variable]

    assert environment_value(variable, template_path) == compose_default(variable, compose_path)


@pytest.mark.parametrize("variable", sorted({*GROUP_ID_SOURCES, *ENVIRONMENT_SOURCES}))
def test_the_sandbox_env_generator_pins_the_same_group(variable):
    _, compose_path = {**GROUP_ID_SOURCES, **ENVIRONMENT_SOURCES}[variable]

    assert generator_pin(variable) == compose_default(variable, compose_path)
