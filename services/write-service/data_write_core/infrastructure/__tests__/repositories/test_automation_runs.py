"""Round-trips for the run ledger.

The engine's whole idempotence rests on one unique constraint, and a fake with a
Python set proves nothing about it: two consumers racing is exactly the case the
database has to settle. These go through the real ORM for that reason.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from asgiref.sync import async_to_sync
from django.contrib.auth.models import User
from django.test import TransactionTestCase

from data_write_core.domain.entities import (
    AutomationEffect,
    AutomationEntity,
    AutomationTrigger,
)
from data_write_core.infrastructure.repositories import DjangoAutomationRepository

NOW = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)


class AutomationRunLedgerTests(TransactionTestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user(username="rule-owner")
        self.repository = DjangoAutomationRepository()

    def _rule(
        self,
        *,
        trigger_type: str = "event",
        event: str | None = "transaction.created",
        schedule: str | None = None,
        enabled: bool = True,
        created_at: datetime = NOW,
        name: str = "Rule",
    ) -> AutomationEntity:
        automation = AutomationEntity(
            id=str(uuid4()),
            user_id=str(self.user.id),
            user_external_id="user_abc",
            name=name,
            trigger=AutomationTrigger(type=trigger_type, event=event, schedule=schedule),
            effects=(AutomationEffect(type="notify", params={"severity": "info", "title": "Hi"}),),
            created_at=created_at,
            enabled=enabled,
        )

        return async_to_sync(self.repository.create_automation)(automation)

    def _claim(self, automation: AutomationEntity, run_key: str) -> bool:
        return async_to_sync(self.repository.claim_run)(
            UUID(automation.unique_id),
            self.user.id,
            run_key,
            NOW,
        )

    def test_a_key_can_only_be_claimed_once(self):
        automation = self._rule()

        self.assertTrue(self._claim(automation, "transaction:abc"))
        self.assertFalse(self._claim(automation, "transaction:abc"))

    def test_a_different_key_is_a_different_run(self):
        automation = self._rule()

        self.assertTrue(self._claim(automation, "wallet:w1@2026-09-01"))
        self.assertTrue(self._claim(automation, "wallet:w1@2026-09-02"))

    def test_two_rules_claim_the_same_subject_independently(self):
        """The constraint is per RULE, not per transaction: two rules both
        matching one transaction is the ordinary case, not a collision."""

        first = self._rule(name="first")
        second = self._rule(name="second")

        self.assertTrue(self._claim(first, "transaction:abc"))
        self.assertTrue(self._claim(second, "transaction:abc"))

    def test_recording_a_run_increments_rather_than_rewrites(self):
        """A run is concurrent with the user editing that rule, so a counter
        must not carry a stale condition back with it."""

        automation = self._rule()

        first = async_to_sync(self.repository.record_run)(UUID(automation.unique_id), NOW)
        second = async_to_sync(self.repository.record_run)(UUID(automation.unique_id), NOW)

        self.assertEqual((first, second), (1, 2))

    def test_scheduled_rules_are_listed_across_users(self):
        """The sweeper has no request and no user to scope itself to."""

        other = User.objects.create_user(username="second-owner")
        mine = self._rule(trigger_type="schedule", event=None, schedule="daily")
        theirs = AutomationEntity(
            id=str(uuid4()),
            user_id=str(other.id),
            user_external_id="user_xyz",
            name="Theirs",
            trigger=AutomationTrigger(type="schedule", schedule="daily"),
            effects=(AutomationEffect(type="notify", params={}),),
            created_at=NOW,
        )
        async_to_sync(self.repository.create_automation)(theirs)

        listed = async_to_sync(self.repository.list_live_scheduled)("daily")

        self.assertEqual(
            {rule.unique_id for rule in listed},
            {mine.unique_id, theirs.unique_id},
        )

    def test_a_disabled_scheduled_rule_is_not_listed(self):
        self._rule(trigger_type="schedule", event=None, schedule="daily", enabled=False)

        self.assertEqual(async_to_sync(self.repository.list_live_scheduled)("daily"), [])

    def test_a_rule_on_another_schedule_is_not_listed(self):
        self._rule(trigger_type="schedule", event=None, schedule="monthly")

        self.assertEqual(async_to_sync(self.repository.list_live_scheduled)("daily"), [])
