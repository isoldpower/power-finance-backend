"""Shutdown-signal sources used to stop the consumer loop."""

from data_read_core.shared.kafka_updates import NeverShutdown, SigtermShutdownSignal


def test_sigterm_signal_starts_unrequested():
    assert SigtermShutdownSignal().is_stop_requested() is False


def test_sigterm_request_stop_flips_the_flag():
    signal = SigtermShutdownSignal()
    signal.request_stop()
    assert signal.is_stop_requested() is True


async def test_sigterm_wait_returns_once_stop_requested():
    signal = SigtermShutdownSignal()
    signal.request_stop()
    await signal.wait()


def test_never_shutdown_is_always_unrequested():
    never = NeverShutdown()
    never.request_stop()
    assert never.is_stop_requested() is False
