from datetime import UTC, datetime
from decimal import Decimal

import pytest

from data_write_core.application.commands.automations.engine import (
    AutomationEngine,
    UnknownEffectError,
)
from data_write_core.domain.value_objects import TransactionOrigin

from ..queries.fakes import (
    FakeGoalRepository,
    FakeMoneyFlowRepository,
    FakeTransactionRepository,
    FakeWalletRepository,
    make_checkpoint,
    make_flow,
    make_transaction_entity,
    make_wallet,
)
from ._automation_fakes import (
    EXTERNAL_ID,
    USER_ID,
    FakeAutomationRepository,
    FakeOutboxRepository,
    RecordingEffect,
    make_rule,
)

pytestmark = pytest.mark.django_db(transaction=True)

TX_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
FLOW_ID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
WALLET_ID = "11111111-1111-1111-1111-111111111111"
OTHER_WALLET_ID = "22222222-2222-2222-2222-222222222222"

COFFEE = {"field_name": "name", "operator": "icontains", "value": "coffee"}
BIG = {"field_name": "amount", "operator": "lte", "value": "-100.00"}


class Harness:
    def __init__(
        self,
        rules,
        *,
        name: str = "Blue Bottle Coffee",
        amount: str = "-4.50",
        origin: TransactionOrigin = TransactionOrigin.MANUAL,
        deleted_at: datetime | None = None,
        wallets=None,
        failing: str = "",
    ) -> None:
        self.log: list[tuple[str, str]] = []
        self.automations = FakeAutomationRepository(rules)
        self.outbox = FakeOutboxRepository()

        transaction = make_transaction_entity(
            TX_ID,
            WALLET_ID,
            name=name,
            origin=origin,
            deleted_at=deleted_at,
        )
        flow = make_flow(FLOW_ID, WALLET_ID, amount, transaction_id=TX_ID)
        self.wallets = wallets or [make_wallet(WALLET_ID, title="Everyday")]
        wallet_repository = FakeWalletRepository(self.wallets)

        self.engine = AutomationEngine(
            executors={
                "notify": RecordingEffect("notify", self.log, fails=failing == "notify"),
                "set_category": RecordingEffect(
                    "set_category",
                    self.log,
                    fails=failing == "set_category",
                ),
                "transfer": RecordingEffect("transfer", self.log, fails=failing == "transfer"),
            },
            automation_repository=self.automations,
            transaction_repository=FakeTransactionRepository([transaction]),
            money_flow_repository=FakeMoneyFlowRepository(
                unsettled={WALLET_ID: [flow]},
                user_transactions=[flow],
                checkpoints={
                    wallet.unique_id: make_checkpoint(
                        wallet.unique_id,
                        "500.00",
                        datetime(2026, 1, 1),
                    )
                    for wallet in self.wallets
                },
            ),
            wallet_repository=wallet_repository,
            goal_repository=FakeGoalRepository(),
            container_repository=wallet_repository.as_containers(),
            outbox_repository=self.outbox,
        )

    async def run(self, event: str = "transaction.created") -> list[str]:
        return await self.engine.run_for_transaction(USER_ID, EXTERNAL_ID, TX_ID, event)

    @property
    def applied(self) -> list[str]:
        return [name for name, _ in self.log]


async def test_a_matching_rule_applies_its_effects():
    harness = Harness([make_rule(filter_body={"and": [COFFEE]})])

    assert await harness.run()
    assert harness.applied == ["notify"]


async def test_a_rule_whose_condition_does_not_match_does_nothing():
    harness = Harness([make_rule(filter_body={"and": [BIG]})])

    assert await harness.run() == []
    assert harness.log == []


async def test_a_rule_with_no_condition_always_matches():
    harness = Harness([make_rule(filter_body=None)])

    assert await harness.run()


async def test_only_rules_for_that_event_are_evaluated():
    harness = Harness([make_rule(filter_body=None, event="transaction.updated")])

    assert await harness.run("transaction.created") == []


async def test_a_disabled_rule_does_not_run():
    harness = Harness([make_rule(filter_body=None, enabled=False)])

    assert await harness.run() == []


async def test_a_deleted_rule_stops_evaluating_immediately():
    rule = make_rule(filter_body=None)
    rule.soft_delete(datetime(2026, 2, 1, tzinfo=UTC))
    harness = Harness([rule])

    assert await harness.run() == []


async def test_rules_run_oldest_first_so_that_the_last_one_wins():
    older = make_rule(
        name="older",
        effects=("set_category",),
        filter_body=None,
        created_at=datetime(2026, 1, 1),
    )
    newer = make_rule(
        name="newer",
        effects=("notify",),
        filter_body=None,
        created_at=datetime(2026, 6, 1),
    )
    harness = Harness([newer, older])

    await harness.run()

    assert harness.applied == ["set_category", "notify"]


async def test_effects_apply_in_the_order_the_rule_lists_them():
    harness = Harness([make_rule(effects=("transfer", "notify"), filter_body=None)])

    await harness.run()

    assert harness.applied == ["transfer", "notify"]


async def test_a_redelivered_event_does_not_run_the_rule_again():
    harness = Harness([make_rule(filter_body=None, effects=("transfer",))])

    assert await harness.run()
    assert await harness.run() == []
    assert harness.applied == ["transfer"]


async def test_a_later_edit_does_not_re_run_a_rule_that_already_saw_the_transaction():
    harness = Harness([make_rule(filter_body=None, event="transaction.created")])
    await harness.run("transaction.created")

    updating = make_rule(filter_body=None, event="transaction.updated")
    harness.automations.automations.append(updating)

    assert await harness.run("transaction.updated")
    assert harness.applied == ["notify", "notify"]


async def test_a_transaction_an_automation_created_never_triggers_a_rule():
    harness = Harness(
        [make_rule(filter_body=None)],
        origin=TransactionOrigin.AUTOMATION,
    )

    assert await harness.run() == []
    assert harness.log == []


async def test_a_cancelled_transaction_is_not_worth_a_rule():
    harness = Harness([make_rule(filter_body=None)], deleted_at=datetime(2026, 2, 1))

    assert await harness.run() == []


async def test_a_run_that_applied_effects_is_counted_and_announced():
    harness = Harness([make_rule(filter_body=None)])

    await harness.run()

    assert harness.automations.recorded
    assert [entry.event_type for entry in harness.outbox.entries] == ["AutomationRan"]


async def test_the_announced_count_is_the_new_total():
    harness = Harness([make_rule(filter_body=None)])

    await harness.run()

    assert harness.outbox.entries[0].payload["runs"] == 1


async def test_an_evaluation_that_did_not_match_is_not_a_run():
    harness = Harness([make_rule(filter_body={"and": [BIG]})])

    await harness.run()

    assert harness.automations.recorded == []
    assert harness.outbox.entries == []


async def test_a_run_that_fails_partway_keeps_what_it_already_did():
    harness = Harness(
        [make_rule(effects=("notify", "transfer"), filter_body=None)],
        failing="transfer",
    )

    assert await harness.run() == []
    assert harness.applied == ["notify", "transfer"]


async def test_a_failed_run_is_not_counted():
    harness = Harness([make_rule(effects=("notify",), filter_body=None)], failing="notify")

    await harness.run()

    assert harness.automations.recorded == []
    assert harness.outbox.entries == []


async def test_a_failed_run_is_not_retried_on_redelivery():
    harness = Harness(
        [make_rule(effects=("notify", "transfer"), filter_body=None)],
        failing="transfer",
    )
    await harness.run()
    await harness.run()

    assert harness.applied == ["notify", "transfer"]


async def test_one_broken_rule_does_not_stop_the_others():
    broken = make_rule(
        name="broken",
        effects=("transfer",),
        filter_body=None,
        created_at=datetime(2026, 1, 1),
    )
    working = make_rule(
        name="working",
        effects=("notify",),
        filter_body=None,
        created_at=datetime(2026, 6, 1),
    )
    harness = Harness([broken, working], failing="transfer")

    assert await harness.run() == [working.unique_id]


async def test_a_rule_carrying_an_effect_this_build_cannot_run_is_refused():
    harness = Harness([make_rule(effects=("teleport",), filter_body=None)])

    assert await harness.run() == []


async def test_a_condition_the_policy_no_longer_accepts_does_not_match():
    stale = make_rule(
        name="stale",
        filter_body={"field_name": "zero_balance", "operator": "eq", "value": "0.00"},
        created_at=datetime(2026, 1, 1),
    )
    working = make_rule(name="working", filter_body=None, created_at=datetime(2026, 6, 1))
    harness = Harness([stale, working])

    assert await harness.run() == [working.unique_id]


async def test_a_scheduled_rule_runs_once_per_wallet():
    harness = Harness(
        [make_rule(trigger_type="schedule", schedule="daily", filter_body=None)],
        wallets=[
            make_wallet(WALLET_ID, title="Everyday"),
            make_wallet(OTHER_WALLET_ID, title="Savings"),
        ],
    )

    applied = await harness.engine.run_scheduled("daily", datetime(2026, 9, 1, tzinfo=UTC))

    assert len(applied) == 2


async def test_a_scheduled_rule_does_not_run_twice_in_the_same_period():
    harness = Harness([make_rule(trigger_type="schedule", schedule="daily", filter_body=None)])

    await harness.engine.run_scheduled("daily", datetime(2026, 9, 1, 6, tzinfo=UTC))
    again = await harness.engine.run_scheduled("daily", datetime(2026, 9, 1, 23, tzinfo=UTC))

    assert again == []


async def test_a_scheduled_rule_runs_again_in_the_next_period():
    harness = Harness([make_rule(trigger_type="schedule", schedule="daily", filter_body=None)])

    await harness.engine.run_scheduled("daily", datetime(2026, 9, 1, tzinfo=UTC))
    tomorrow = await harness.engine.run_scheduled("daily", datetime(2026, 9, 2, tzinfo=UTC))

    assert tomorrow


async def test_a_scheduled_condition_is_matched_against_the_wallet():
    rich = {"field_name": "balance", "operator": "gte", "value": "400.00"}
    harness = Harness([make_rule(trigger_type="schedule", schedule="daily", filter_body=rich)])

    assert await harness.engine.run_scheduled("daily", datetime(2026, 9, 1, tzinfo=UTC))


async def test_a_scheduled_condition_that_does_not_match_the_wallet_does_nothing():
    poor = {"field_name": "balance", "operator": "lte", "value": "1.00"}
    harness = Harness([make_rule(trigger_type="schedule", schedule="daily", filter_body=poor)])

    assert await harness.engine.run_scheduled("daily", datetime(2026, 9, 1, tzinfo=UTC)) == []


def test_the_unknown_effect_error_names_the_type():
    assert "teleport" in str(UnknownEffectError("teleport"))


def test_the_subject_carries_a_signed_amount():
    from data_write_core.domain.aggregates import TransactionAggregate
    from data_write_core.domain.services import transaction_subject

    aggregate = TransactionAggregate(
        transaction_entity=make_transaction_entity(TX_ID, WALLET_ID, name="Coffee"),
        flows=[make_flow(FLOW_ID, WALLET_ID, "-4.50", transaction_id=TX_ID)],
    )

    subject = transaction_subject(aggregate, "USD")

    assert subject["amount"] == Decimal("-4.50")
    assert subject["type"] == "expense"
    assert "category" not in subject
