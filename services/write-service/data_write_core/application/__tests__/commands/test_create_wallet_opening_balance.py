from datetime import datetime
from decimal import Decimal
from uuid import UUID

from data_write_core.application.commands.transactions.transaction_factory import (
    build_transaction,
)
from data_write_core.application.commands.wallets.create_new_wallet import (
    OPENING_BALANCE_NAME,
    UNSET,
    CreateNewWalletCommand,
    CreateNewWalletCommandHandler,
)
from data_write_core.domain.aggregates import TransactionAggregate
from data_write_core.domain.entities import TransactionEntity, WalletEntity
from data_write_core.domain.value_objects import (
    MoneyContainerKind,
    MoneyContainerRef,
    TransactionMetadata,
    WalletData,
)

WALLET_ID = "11111111-1111-1111-1111-111111111111"


def _command(**overrides) -> CreateNewWalletCommand:
    defaults = {
        "user_id": 7,
        "user_external_id": "user_abc",
        "name": "New Card",
        "currency": "USD",
    }
    defaults.update(overrides)
    return CreateNewWalletCommand(**defaults)


def _wallet(zero_balance: str = "0", currency_code: str = "USD") -> WalletEntity:
    moment = datetime(2026, 1, 1)
    return WalletEntity.create(
        id=WALLET_ID,
        user_id="7",
        data=WalletData(
            title="New Card",
            currency_code=currency_code,
            zero_balance=Decimal(zero_balance),
        ),
        created_at=moment,
        updated_at=moment,
    )


class TestOpeningBalanceDefault:
    def test_an_omitted_opening_balance_lands_on_the_datum(self):
        """A wallet nobody funded should open owning and owing nothing, which
        for a credit line means opening at its limit, not at zero."""

        resolved = CreateNewWalletCommandHandler._resolve_opening_balance(
            _command(zero_balance=Decimal("100"), opening_balance=UNSET)
        )

        assert resolved == Decimal("100")

    def test_an_ordinary_wallet_still_opens_empty(self):
        resolved = CreateNewWalletCommandHandler._resolve_opening_balance(_command())

        assert resolved == Decimal("0")

    def test_an_explicit_opening_balance_wins_over_the_datum(self):
        resolved = CreateNewWalletCommandHandler._resolve_opening_balance(
            _command(zero_balance=Decimal("100"), opening_balance=Decimal("70"))
        )

        assert resolved == Decimal("70")


class TestOpeningOutboxEntries:
    def _opening_transaction(self, amount: str) -> TransactionAggregate:
        return build_transaction(
            user_id=7,
            container=MoneyContainerRef(
                id=UUID(WALLET_ID),
                kind=MoneyContainerKind.WALLET,
                currency_code="USD",
                title="Main",
            ),
            metadata=TransactionMetadata(name=OPENING_BALANCE_NAME),
            amount=abs(Decimal(amount)),
            transaction_type=TransactionEntity.type_for(Decimal(amount)),
            created_at=datetime(2026, 1, 1),
        )

    def test_a_funded_wallet_emits_the_wallet_then_the_transaction(self):
        """Order is load-bearing: the transaction projection reads the wallet
        row for its currency, and both entries share a partition key."""

        entries = CreateNewWalletCommandHandler._outbox_entries(
            _wallet(),
            self._opening_transaction("50.00"),
            partition_key="user_abc",
        )

        assert [entry.event_type for entry in entries] == [
            "WalletCreated",
            "TransactionCreated",
        ]
        assert [entry.aggregate_type for entry in entries] == ["wallet", "transaction"]
        assert {entry.partition_key for entry in entries} == {"user_abc"}

    def test_an_unfunded_wallet_emits_no_transaction(self):
        entries = CreateNewWalletCommandHandler._outbox_entries(
            _wallet(),
            None,
            partition_key="user_abc",
        )

        assert [entry.event_type for entry in entries] == ["WalletCreated"]

    def test_the_transaction_is_linked_to_the_wallet_it_opens(self):
        opening = self._opening_transaction("50.00")

        assert opening.origin_flow.container_id == UUID(WALLET_ID)
        assert opening.amount == Decimal("50.00")
        assert opening.root.name == OPENING_BALANCE_NAME

    def test_the_opening_transaction_is_denominated_in_the_wallet_s_currency(self):
        """The opening balance is a real transaction, so ai-service posts it
        like any other and needs a currency for it. The only source is the
        wallet being created — there is no container row to read yet."""

        entries = CreateNewWalletCommandHandler._outbox_entries(
            _wallet(currency_code="JPY"),
            self._opening_transaction("50.00"),
            partition_key="user_abc",
        )

        assert entries[1].payload["currency_code"] == "JPY"

    def test_the_wallet_event_carries_the_datum_as_a_decimal_string(self):
        entries = CreateNewWalletCommandHandler._outbox_entries(
            _wallet(zero_balance="100.00"),
            None,
            partition_key="user_abc",
        )

        assert entries[0].payload["zero_balance"] == "100.00"
