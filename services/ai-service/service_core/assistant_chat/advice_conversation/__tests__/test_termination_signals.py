"""The signals a conversation can be ended by."""

from ..contracts import Termination, TerminationReason
from ..signals import NeverTerminates, ProcessShutdownSignal


async def test_a_fresh_shutdown_signal_has_not_fired():
    assert ProcessShutdownSignal().is_terminated() is False


async def test_a_terminated_signal_reports_the_reason_it_was_given():
    signal = ProcessShutdownSignal()

    signal.terminate(Termination.server_shutting_down())

    assert signal.is_terminated() is True
    assert (await signal.wait()).code == TerminationReason.GOING_AWAY


async def test_the_never_terminating_signal_never_reports_termination():
    assert NeverTerminates().is_terminated() is False
