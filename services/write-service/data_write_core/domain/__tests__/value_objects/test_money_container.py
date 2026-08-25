from decimal import Decimal
from uuid import UUID

from django.test import SimpleTestCase

from data_write_core.domain.aggregates import MoneyContainerAggregate
from data_write_core.domain.value_objects import MoneyContainerKind, MoneyContainerRef

CONTAINER_ID = UUID("44444444-4444-4444-4444-444444444444")


def _reference(kind: MoneyContainerKind) -> MoneyContainerRef:
    return MoneyContainerRef(
        id=CONTAINER_ID,
        kind=kind,
        currency_code="USD",
        title="Anything",
    )


class MoneyContainerRefTests(SimpleTestCase):
    def test_a_wallet_reference_knows_it_is_a_wallet(self) -> None:
        reference = _reference(MoneyContainerKind.WALLET)

        assert reference.is_wallet is True
        assert reference.is_goal is False

    def test_a_goal_reference_knows_it_is_a_goal(self) -> None:
        reference = _reference(MoneyContainerKind.GOAL)

        assert reference.is_goal is True
        assert reference.is_wallet is False

    def test_references_are_frozen(self) -> None:
        reference = _reference(MoneyContainerKind.WALLET)

        with self.assertRaises(Exception):
            reference.kind = MoneyContainerKind.GOAL  # type: ignore[misc]

    def test_a_reference_opens_unclosed(self) -> None:
        assert _reference(MoneyContainerKind.WALLET).is_closed is False

    def test_the_kind_serialises_as_its_wire_value(self) -> None:
        """The proto field and the read-side column both carry the bare string."""

        assert str(MoneyContainerKind.WALLET) == "wallet"
        assert str(MoneyContainerKind.GOAL) == "goal"


class ContainerProtocolTests(SimpleTestCase):
    """Both aggregates have to satisfy the protocol the transaction path depends on.

    A structural check rather than a nominal one: nothing inherits from the protocol,
    so only this asserts the two stay interchangeable.
    """

    def test_the_wallet_aggregate_is_a_money_container(self) -> None:
        from datetime import datetime

        from data_write_core.domain.aggregates import WalletAggregate
        from data_write_core.domain.entities import WalletEntity
        from data_write_core.domain.value_objects import WalletData

        aggregate = WalletAggregate(
            wallet_entity=WalletEntity.create(
                id=str(CONTAINER_ID),
                data=WalletData(title="Main", currency_code="USD"),
                user_id="9",
                created_at=datetime(2026, 1, 1),
                updated_at=datetime(2026, 1, 1),
            ),
            unsettled_transactions=[],
            balance_checkpoint=None,
        )

        assert isinstance(aggregate, MoneyContainerAggregate)
        assert aggregate.balance == Decimal("0")
        assert aggregate.currency_code == "USD"

    def test_the_goal_aggregate_is_a_money_container(self) -> None:
        from datetime import datetime

        from data_write_core.domain.aggregates import GoalAggregate
        from data_write_core.domain.entities import GoalEntity
        from data_write_core.domain.value_objects import GoalData

        aggregate = GoalAggregate(
            goal_entity=GoalEntity.create(
                id=str(CONTAINER_ID),
                data=GoalData(title="Bike", currency_code="USD", target=Decimal("500")),
                user_id="9",
                created_at=datetime(2026, 1, 1),
            ),
            unsettled_flows=[],
            balance_checkpoint=None,
        )

        assert isinstance(aggregate, MoneyContainerAggregate)
        assert aggregate.balance == Decimal("0")
        assert aggregate.currency_code == "USD"
