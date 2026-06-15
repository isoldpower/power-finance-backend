"""EventCollector collect / pull / close semantics: pull is destructive,
close_after locks writes, and pull still drains a closed collector."""

from __future__ import annotations

from dataclasses import dataclass

from django.test import SimpleTestCase

from data_write_core.domain.events import DomainEvent, EventCollector
from data_write_core.domain.exceptions import EventCollectorClosedError


@dataclass(frozen=True)
class _Marker(DomainEvent):
    label: str = "x"


class EventCollectorTests(SimpleTestCase):
    def test_collect_appends_events_in_order(self) -> None:
        collector = EventCollector()

        first = _Marker(label="a")
        second = _Marker(label="b")
        collector.collect(first)
        collector.collect(second)

        self.assertEqual(collector.pull_events(), [first, second])

    def test_pull_events_drains_the_buffer(self) -> None:
        collector = EventCollector()
        collector.collect(_Marker(label="x"))

        first_pull = collector.pull_events()
        second_pull = collector.pull_events()

        self.assertEqual(len(first_pull), 1)
        self.assertEqual(second_pull, [])

    def test_pull_returns_independent_list_snapshot(self) -> None:
        collector = EventCollector()
        collector.collect(_Marker(label="x"))

        pulled = collector.pull_events()
        pulled.append(_Marker(label="injected"))
        collector.collect(_Marker(label="y"))

        self.assertEqual(len(collector.pull_events()), 1)

    def test_collect_close_after_blocks_subsequent_collects(self) -> None:
        collector = EventCollector()

        collector.collect(_Marker(label="last"), close_after=True)

        with self.assertRaises(EventCollectorClosedError):
            collector.collect(_Marker(label="too late"))

    def test_pull_close_after_blocks_subsequent_collects(self) -> None:
        collector = EventCollector()
        collector.collect(_Marker(label="x"))

        events = collector.pull_events(close_after=True)

        self.assertEqual(len(events), 1)
        with self.assertRaises(EventCollectorClosedError):
            collector.collect(_Marker(label="nope"))

    def test_pull_on_closed_collector_still_returns_empty(self) -> None:
        collector = EventCollector()
        collector.pull_events(close_after=True)

        self.assertEqual(collector.pull_events(), [])
