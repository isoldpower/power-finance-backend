import pytest

from data_write_core.application.bootstrap.event_bus import initialize_event_bus
from data_write_core.application.commands import _command_base


@pytest.fixture(autouse=True)
def in_process_event_bus(monkeypatch):
    """Make a command handler's `_publish_domain_events` call work off-infrastructure.

    The bus is the only piece of the bootstrapped application a handler reaches
    for after its saga commits. Without it every test has to stop at the
    validation branch, which is why the handlers were half-covered.
    """

    event_bus = initialize_event_bus()
    monkeypatch.setattr(_command_base, "get_event_bus", lambda: event_bus)

    return event_bus
