"""What the scaffolding dispatcher promises, so the pipeline around it has
something fixed to be built against."""

from decimal import Decimal
from uuid import UUID

import pytest

from ..contracts import AccountSpec
from ..dispatchers import TemplateAccount, TemplateDispatcher
from .fakes import (
    TEMPLATE_ACCOUNTS,
    USER_ID,
    StubAccountRepository,
    build_template_dispatcher,
    build_transaction_facts,
)

LIABILITY_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
ASSETS_ID = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")


def _accounts() -> StubAccountRepository:
    return StubAccountRepository(
        {
            TEMPLATE_ACCOUNTS[0].specification: LIABILITY_ID,
            TEMPLATE_ACCOUNTS[1].specification: ASSETS_ID,
        }
    )


async def test_the_template_names_a_debited_liability_and_a_credited_asset():
    assert [
        (account.specification.group, account.specification.name, account.debit)
        for account in TEMPLATE_ACCOUNTS
    ] == [
        ("liabilities", "temporary-liability", True),
        ("assets", "temporary-assets", False),
    ]


async def test_legs_point_at_the_accounts_the_repository_resolved():
    postings = await build_template_dispatcher(_accounts()).dispatch(build_transaction_facts())

    assert [(leg.account_id, leg.debit) for leg in postings.legs] == [
        (LIABILITY_ID, True),
        (ASSETS_ID, False),
    ]


async def test_the_accounts_are_looked_up_for_the_transaction_s_owner():
    """Accounts are per-user, so a dispatcher that resolved them once at
    construction would post everyone's legs against one user's chart."""

    accounts = _accounts()

    await build_template_dispatcher(accounts).dispatch(build_transaction_facts())

    assert accounts.resolved_for == [USER_ID]


async def test_both_legs_carry_the_transaction_amount():
    postings = await build_template_dispatcher(_accounts()).dispatch(
        build_transaction_facts(amount=Decimal("125.00"))
    )

    assert [leg.amount for leg in postings.legs] == [Decimal("125.00"), Decimal("125.00")]
    assert postings.balanced is True


async def test_a_negative_amount_still_produces_positive_legs():
    """Direction is what `debit` says, not what the sign says. A leg carrying a
    negative amount would double-count the direction."""

    postings = await build_template_dispatcher(_accounts()).dispatch(
        build_transaction_facts(amount=Decimal("-40.00"))
    )

    assert [leg.amount for leg in postings.legs] == [Decimal("40.00"), Decimal("40.00")]


async def test_legs_carry_the_transaction_s_currency():
    """A leg is a claim about money, and money without a unit is a number. The
    currency comes from the container the transaction was created against."""

    postings = await build_template_dispatcher(_accounts()).dispatch(
        build_transaction_facts(currency_code="JPY")
    )

    assert {leg.currency_code for leg in postings.legs} == {"JPY"}


async def test_a_transaction_with_no_known_currency_leaves_the_legs_undenominated():
    """Transactions projected before `TransactionCreated` carried a currency
    keep an empty code. Storing that as `""` would claim the currency is known
    and empty; `None` says it was never recorded."""

    postings = await build_template_dispatcher(_accounts()).dispatch(
        build_transaction_facts(currency_code="")
    )

    assert {leg.currency_code for leg in postings.legs} == {None}


async def test_positions_order_the_legs():
    postings = await build_template_dispatcher(_accounts()).dispatch(build_transaction_facts())

    assert [leg.position for leg in postings.legs] == [0, 1]


async def test_the_backend_names_itself_as_scaffolding():
    postings = await build_template_dispatcher(_accounts()).dispatch(build_transaction_facts())

    assert postings.backend == "template"


async def test_a_different_template_is_a_constructor_argument():
    """The point of taking the accounts rather than naming them inline: a second
    template is configuration, not an edit to the dispatcher."""

    specification = AccountSpec(group="equity", name="opening-balance")
    accounts = StubAccountRepository({specification: LIABILITY_ID})

    postings = await TemplateDispatcher(
        accounts, [TemplateAccount(specification, debit=False)]
    ).dispatch(build_transaction_facts())

    assert [(leg.account_id, leg.debit) for leg in postings.legs] == [(LIABILITY_ID, False)]


async def test_an_unresolvable_account_is_not_swallowed():
    with pytest.raises(KeyError):
        await build_template_dispatcher(StubAccountRepository({})).dispatch(
            build_transaction_facts()
        )
