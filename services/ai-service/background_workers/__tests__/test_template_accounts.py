"""The chart the service runs on, against the chart service_core's tests assume.

`user_created` seeds the accounts `transaction_created` and `transaction_updated`
later resolve, so those three charts must name the same accounts — a drift is an
`UnknownAccountsError` at runtime, not a wrong number.

service_core cannot assert this: it may not import the wiring layer. The wiring
layer may import service_core, so the check lives here.
"""

from service_core.write_reactions.__tests__.template import (
    TEMPLATE as SERVICE_CORE_TEMPLATE,
)

from ..services.build_event_router._template_accounts import (
    CREATED_TEMPLATE_ACCOUNTS,
    SEED_TEMPLATE_ACCOUNTS,
    UPDATED_TEMPLATE_ACCOUNTS,
)


def _triples(accounts) -> tuple[tuple[str, str, bool], ...]:
    return tuple(
        (account.specification.group, account.specification.name, account.debit)
        for account in accounts
    )


def test_the_seeded_chart_is_the_one_the_dispatchers_resolve():
    """The invariant that actually breaks at runtime: an account the seeding
    slice never created cannot be resolved by a dispatching one."""

    assert _triples(SEED_TEMPLATE_ACCOUNTS) == _triples(CREATED_TEMPLATE_ACCOUNTS)
    assert _triples(SEED_TEMPLATE_ACCOUNTS) == _triples(UPDATED_TEMPLATE_ACCOUNTS)


def test_the_wired_chart_is_the_one_service_core_is_tested_against():
    """Otherwise service_core's suite proves the reactions work on a chart the
    service does not actually run on."""

    assert _triples(SEED_TEMPLATE_ACCOUNTS) == SERVICE_CORE_TEMPLATE
