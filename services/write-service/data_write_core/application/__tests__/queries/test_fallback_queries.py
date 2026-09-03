from datetime import datetime
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest
from write_service.common.pagination import (
    ACTION_QUEUE,
    CURSOR_CODEC,
    PageRequest,
    build_page,
    query_fingerprint,
)

from data_write_core.application.queries import (
    CountFallbackNotificationsQuery,
    CountFallbackNotificationsQueryHandler,
    FallbackActionFilters,
    FallbackAutomationFilters,
    GetFallbackAutomationQuery,
    GetFallbackAutomationQueryHandler,
    GetFallbackGoalQuery,
    GetFallbackGoalQueryHandler,
    GetFallbackTransactionQuery,
    GetFallbackTransactionQueryHandler,
    GetFallbackWalletQuery,
    GetFallbackWalletQueryHandler,
    ListFallbackActionsQuery,
    ListFallbackActionsQueryHandler,
    ListFallbackAutomationsQuery,
    ListFallbackAutomationsQueryHandler,
    ListFallbackGoalsQuery,
    ListFallbackGoalsQueryHandler,
    ListFallbackTransactionsQuery,
    ListFallbackTransactionsQueryHandler,
    ListFallbackWalletsQuery,
    ListFallbackWalletsQueryHandler,
)

from .fakes import (
    FakeActionRepository,
    FakeAutomationRepository,
    FakeGoalRepository,
    FakeMoneyFlowRepository,
    FakeNotificationRepository,
    FakeTransactionRepository,
    FakeWalletRepository,
    make_action,
    make_automation,
    make_checkpoint,
    make_flow,
    make_goal,
    make_notification,
    make_page,
    make_transaction_entity,
    make_wallet,
)

WALLET_A = "11111111-1111-1111-1111-111111111111"
WALLET_B = "22222222-2222-2222-2222-222222222222"
TX_1 = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
TX_2 = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
TX_EFFECT = "cccccccc-cccc-cccc-cccc-cccccccccccc"
GOAL_A = "44444444-4444-4444-4444-444444444444"
GOAL_B = "55555555-5555-5555-5555-555555555555"


async def test_get_wallet_folds_unsettled_onto_checkpoint():
    wallet_repo = FakeWalletRepository([make_wallet(WALLET_A, currency="EUR")])
    transaction_repo = FakeMoneyFlowRepository(
        checkpoints={WALLET_A: make_checkpoint(WALLET_A, "100", datetime(2026, 1, 1))},
        unsettled={
            WALLET_A: [
                make_flow(TX_1, WALLET_A, "50"),
                make_flow(TX_2, WALLET_A, "-20"),
            ]
        },
    )
    handler = GetFallbackWalletQueryHandler(wallet_repo, transaction_repo)

    detail = await handler.handle(
        GetFallbackWalletQuery(user_id=7, wallet_id=UUID(WALLET_A), zone=ZoneInfo("UTC"))
    )

    assert detail.wallet.balance_amount == Decimal("130")
    assert detail.wallet.currency == "EUR"


async def test_get_wallet_with_no_checkpoint_starts_at_zero():
    wallet_repo = FakeWalletRepository([make_wallet(WALLET_A)])
    transaction_repo = FakeMoneyFlowRepository(
        unsettled={WALLET_A: [make_flow(TX_1, WALLET_A, "42")]},
    )
    handler = GetFallbackWalletQueryHandler(wallet_repo, transaction_repo)

    detail = await handler.handle(
        GetFallbackWalletQuery(user_id=7, wallet_id=UUID(WALLET_A), zone=ZoneInfo("UTC"))
    )

    assert detail.wallet.balance_amount == Decimal("42")


async def test_list_wallets_returns_dtos_with_balances_and_total():
    wallets = [
        make_wallet(WALLET_A, created_at=datetime(2026, 1, 2)),
        make_wallet(WALLET_B, created_at=datetime(2026, 1, 1)),
    ]
    wallet_repo = FakeWalletRepository(wallets)
    transaction_repo = FakeMoneyFlowRepository(
        checkpoints={
            WALLET_A: make_checkpoint(WALLET_A, "10", datetime(2026, 1, 1)),
            WALLET_B: make_checkpoint(WALLET_B, "5", datetime(2026, 1, 1)),
        },
    )
    handler = ListFallbackWalletsQueryHandler(wallet_repo, transaction_repo)

    dtos, total = await handler.handle(
        ListFallbackWalletsQuery(user_id=7, page=make_page(limit=20))
    )

    assert total == 2
    assert [str(built_dto.id) for built_dto in dtos] == [WALLET_A, WALLET_B]
    assert dtos[0].balance_amount == Decimal("10")


async def test_list_wallets_pages_forward_from_a_cursor():
    """The second page starts after the first page's last row, not at an offset."""

    wallets = [
        make_wallet(WALLET_A, created_at=datetime(2026, 1, 2)),
        make_wallet(WALLET_B, created_at=datetime(2026, 1, 1)),
    ]
    handler = ListFallbackWalletsQueryHandler(
        FakeWalletRepository(wallets), FakeMoneyFlowRepository()
    )

    first_request = make_page(limit=1)
    first_rows, total = await handler.handle(
        ListFallbackWalletsQuery(user_id=7, page=first_request)
    )
    first_page = build_page(first_rows, total, first_request)

    second_request = make_page(
        limit=1,
        cursor=CURSOR_CODEC.decode(first_page.next_cursor, first_request.fingerprint),
    )
    second_rows, _ = await handler.handle(ListFallbackWalletsQuery(user_id=7, page=second_request))

    assert total == 2
    assert [str(built_dto.id) for built_dto in first_page.items] == [WALLET_A]
    assert [str(built_dto.id) for built_dto in second_rows] == [WALLET_B]


async def test_get_transaction_folds_its_flows_into_one_amount():
    """The amount is the fold of the ledger, not a stored column — an
    adjustment moves it without anything being rewritten."""

    wallet_repo = FakeWalletRepository([make_wallet(WALLET_A, currency="GBP")])
    flow_repo = FakeMoneyFlowRepository(
        unsettled={
            WALLET_A: [
                make_flow(TX_1, WALLET_A, "-12.50", transaction_id=TX_1),
                make_flow(TX_EFFECT, WALLET_A, "-2.50", transaction_id=TX_1),
            ]
        }
    )
    transaction_repo = FakeTransactionRepository([make_transaction_entity(TX_1, WALLET_A)])
    handler = GetFallbackTransactionQueryHandler(
        flow_repo, wallet_repo.as_containers(), transaction_repo
    )

    built_dto = await handler.handle(
        GetFallbackTransactionQuery(user_id=7, transaction_id=UUID(TX_1))
    )

    assert built_dto.currency_code == "GBP"
    assert built_dto.amount == Decimal("15.00")
    assert str(built_dto.transaction_type) == "expense"


async def test_get_transaction_reports_direction_from_the_sign():
    wallet_repo = FakeWalletRepository([make_wallet(WALLET_A, currency="USD")])
    flow_repo = FakeMoneyFlowRepository(
        unsettled={WALLET_A: [make_flow(TX_1, WALLET_A, "40.00", transaction_id=TX_1)]}
    )
    transaction_repo = FakeTransactionRepository([make_transaction_entity(TX_1, WALLET_A)])
    handler = GetFallbackTransactionQueryHandler(
        flow_repo, wallet_repo.as_containers(), transaction_repo
    )

    built_dto = await handler.handle(
        GetFallbackTransactionQuery(user_id=7, transaction_id=UUID(TX_1))
    )

    assert str(built_dto.transaction_type) == "income"
    assert built_dto.amount == Decimal("40.00")


async def test_get_transaction_missing_raises():
    handler = GetFallbackTransactionQueryHandler(
        FakeMoneyFlowRepository(),
        FakeWalletRepository([]).as_containers(),
        FakeTransactionRepository(),
    )

    with pytest.raises(ValueError):
        await handler.handle(GetFallbackTransactionQuery(user_id=7, transaction_id=UUID(TX_1)))


async def test_get_transaction_still_resolves_a_cancelled_one():
    """DELETE removes a transaction from lists and search, not from existence,
    and the amount it reports is the one it was FOR."""

    wallet_repo = FakeWalletRepository([make_wallet(WALLET_A, currency="USD")])
    flow_repo = FakeMoneyFlowRepository(
        unsettled={
            WALLET_A: [
                make_flow(TX_1, WALLET_A, "-20", transaction_id=TX_1),
                make_flow(
                    TX_EFFECT,
                    WALLET_A,
                    "20",
                    transaction_id=TX_1,
                    cancels_other=UUID(TX_1),
                ),
            ]
        }
    )
    transaction_repo = FakeTransactionRepository(
        [make_transaction_entity(TX_1, WALLET_A, deleted_at=datetime(2026, 2, 1))]
    )
    handler = GetFallbackTransactionQueryHandler(
        flow_repo, wallet_repo.as_containers(), transaction_repo
    )

    built_dto = await handler.handle(
        GetFallbackTransactionQuery(user_id=7, transaction_id=UUID(TX_1))
    )

    assert built_dto.deleted_at == datetime(2026, 2, 1)
    assert built_dto.amount == Decimal("20")


async def test_list_transactions_sorts_desc_paginates_and_maps_currency():
    wallet_repo = FakeWalletRepository([make_wallet(WALLET_A, currency="USD")])
    flow_repo = FakeMoneyFlowRepository(
        unsettled={
            WALLET_A: [
                make_flow(TX_1, WALLET_A, "-10", transaction_id=TX_1),
                make_flow(TX_2, WALLET_A, "-20", transaction_id=TX_2),
            ]
        }
    )
    transaction_repo = FakeTransactionRepository(
        [
            make_transaction_entity(TX_1, WALLET_A, created_at=datetime(2026, 1, 1)),
            make_transaction_entity(TX_2, WALLET_A, created_at=datetime(2026, 1, 5)),
        ]
    )
    handler = ListFallbackTransactionsQueryHandler(
        flow_repo, wallet_repo.as_containers(), transaction_repo
    )

    dtos, total = await handler.handle(
        ListFallbackTransactionsQuery(user_id=7, page=make_page(limit=1))
    )

    assert total == 2
    assert str(dtos[0].id) == TX_2
    assert dtos[0].currency_code == "USD"


async def test_list_transactions_excludes_cancelled_ones():
    wallet_repo = FakeWalletRepository([make_wallet(WALLET_A, currency="USD")])
    flow_repo = FakeMoneyFlowRepository(
        unsettled={WALLET_A: [make_flow(TX_1, WALLET_A, "-20", transaction_id=TX_1)]}
    )
    transaction_repo = FakeTransactionRepository(
        [make_transaction_entity(TX_1, WALLET_A, deleted_at=datetime(2026, 2, 1))]
    )
    handler = ListFallbackTransactionsQueryHandler(
        flow_repo, wallet_repo.as_containers(), transaction_repo
    )

    dtos, total = await handler.handle(
        ListFallbackTransactionsQuery(user_id=7, page=make_page(limit=20))
    )

    assert total == 0
    assert dtos == []


async def test_list_transactions_carries_the_wallet_label():
    wallet_repo = FakeWalletRepository([make_wallet(WALLET_A, title="Random Credit Card")])
    flow_repo = FakeMoneyFlowRepository(
        unsettled={WALLET_A: [make_flow(TX_1, WALLET_A, "-20", transaction_id=TX_1)]}
    )
    transaction_repo = FakeTransactionRepository([make_transaction_entity(TX_1, WALLET_A)])
    handler = ListFallbackTransactionsQueryHandler(
        flow_repo, wallet_repo.as_containers(), transaction_repo
    )

    dtos, _ = await handler.handle(
        ListFallbackTransactionsQuery(user_id=7, page=make_page(limit=20))
    )

    assert dtos[0].container.name == "Random Credit Card"


async def test_list_goals_returns_the_goals_themselves_not_a_list_holding_them():
    """The page is flat. Gathering the count alongside the goals used to unpack the
    whole page into the first slot, which typed as a list either way."""
    goal_repository = FakeGoalRepository(
        [
            make_goal(GOAL_A, title="Laptop", created_at=datetime(2026, 3, 1)),
            make_goal(GOAL_B, title="Trip", created_at=datetime(2026, 2, 1)),
        ]
    )
    handler = ListFallbackGoalsQueryHandler(goal_repository, FakeMoneyFlowRepository())

    goals, total = await handler.handle(ListFallbackGoalsQuery(user_id=7, page=make_page(limit=25)))

    assert total == 2
    assert [goal.name for goal in goals] == ["Laptop", "Trip"]


async def test_list_goals_folds_unsettled_flows_onto_each_progress():
    goal_repository = FakeGoalRepository([make_goal(GOAL_A, title="Laptop")])
    flow_repository = FakeMoneyFlowRepository(
        checkpoints={GOAL_A: make_checkpoint(GOAL_A, "100", datetime(2026, 1, 1))},
        unsettled={GOAL_A: [make_flow(TX_1, GOAL_A, "50"), make_flow(TX_2, GOAL_A, "-20")]},
    )
    handler = ListFallbackGoalsQueryHandler(goal_repository, flow_repository)

    goals, _ = await handler.handle(ListFallbackGoalsQuery(user_id=7, page=make_page()))

    assert goals[0].progress == Decimal("130")


async def test_list_goals_on_an_empty_page_is_an_empty_list():
    handler = ListFallbackGoalsQueryHandler(FakeGoalRepository(), FakeMoneyFlowRepository())

    goals, total = await handler.handle(ListFallbackGoalsQuery(user_id=7, page=make_page()))

    assert goals == []
    assert total == 0


async def test_get_goal_folds_unsettled_onto_the_checkpoint():
    goal_repository = FakeGoalRepository([make_goal(GOAL_A, target="1000")])
    flow_repository = FakeMoneyFlowRepository(
        checkpoints={GOAL_A: make_checkpoint(GOAL_A, "200", datetime(2026, 1, 1))},
        unsettled={GOAL_A: [make_flow(TX_1, GOAL_A, "-40")]},
    )
    handler = GetFallbackGoalQueryHandler(goal_repository, flow_repository)

    goal = await handler.handle(GetFallbackGoalQuery(user_id=7, goal_id=UUID(GOAL_A)))

    assert goal.progress == Decimal("160")
    assert goal.target == Decimal("1000")


ACTION_INFO = "66666666-6666-6666-6666-666666666666"
ACTION_CRITICAL = "77777777-7777-7777-7777-777777777777"
AUTOMATION_A = "88888888-8888-8888-8888-888888888888"
AUTOMATION_B = "99999999-9999-9999-9999-999999999999"
AUTOMATION_DELETED = "aaaaaaaa-1111-1111-1111-111111111111"
NOTIFICATION_A = "bbbbbbbb-1111-1111-1111-111111111111"
NOTIFICATION_B = "cccccccc-1111-1111-1111-111111111111"


def _action_page(limit: int = 25, cursor=None) -> PageRequest:
    filters = FallbackActionFilters()

    return PageRequest(
        limit=limit,
        order=ACTION_QUEUE,
        fingerprint=query_fingerprint(ACTION_QUEUE, filters.as_cursor_material()),
        cursor=cursor,
    )


async def test_the_action_queue_leads_with_urgency_not_recency():
    """The whole reason actions need their own sort order: a critical action
    raised yesterday outranks an informational one raised a minute ago."""

    repository = FakeActionRepository(
        [
            make_action(ACTION_INFO, severity="info", created_at=datetime(2026, 3, 1)),
            make_action(ACTION_CRITICAL, severity="critical", created_at=datetime(2026, 1, 1)),
        ]
    )
    handler = ListFallbackActionsQueryHandler(repository)

    actions, total = await handler.handle(
        ListFallbackActionsQuery(
            user_id=7,
            page=_action_page(),
            filters=FallbackActionFilters(),
        )
    )

    assert [str(action.id) for action in actions] == [ACTION_CRITICAL, ACTION_INFO]
    assert total == 2


async def test_an_action_carries_the_rank_its_cursor_sorts_on():
    """`severity_rank` never reaches the client, but the page builder reads it
    off the DTO to mint the cursor — so it has to survive the mapping."""

    repository = FakeActionRepository([make_action(ACTION_CRITICAL, severity="critical")])
    handler = ListFallbackActionsQueryHandler(repository)

    actions, _ = await handler.handle(
        ListFallbackActionsQuery(
            user_id=7,
            page=_action_page(),
            filters=FallbackActionFilters(),
        )
    )

    assert actions[0].severity_rank == 3


async def test_the_action_queue_answers_only_the_asked_for_status():
    repository = FakeActionRepository(
        [
            make_action(ACTION_INFO, status="pending"),
            make_action(ACTION_CRITICAL, status="resolved"),
        ]
    )
    handler = ListFallbackActionsQueryHandler(repository)

    actions, total = await handler.handle(
        ListFallbackActionsQuery(
            user_id=7,
            page=_action_page(),
            filters=FallbackActionFilters(),
        )
    )

    assert [str(action.id) for action in actions] == [ACTION_INFO]
    assert total == 1


async def test_the_action_cursor_survives_a_page_turn():
    repository = FakeActionRepository(
        [
            make_action(ACTION_CRITICAL, severity="critical", created_at=datetime(2026, 1, 2)),
            make_action(ACTION_INFO, severity="info", created_at=datetime(2026, 1, 1)),
        ]
    )
    handler = ListFallbackActionsQueryHandler(repository)
    first_request = _action_page(limit=1)

    actions, total = await handler.handle(
        ListFallbackActionsQuery(
            user_id=7,
            page=first_request,
            filters=FallbackActionFilters(),
        )
    )
    first_page = build_page(actions, total, first_request)

    assert [str(action.id) for action in first_page.items] == [ACTION_CRITICAL]

    next_request = _action_page(
        limit=1,
        cursor=CURSOR_CODEC.decode(
            first_page.meta(cached=False)["next_cursor"],
            first_request.fingerprint,
        ),
    )
    following, following_total = await handler.handle(
        ListFallbackActionsQuery(
            user_id=7,
            page=next_request,
            filters=FallbackActionFilters(),
        )
    )

    assert [str(action.id) for action in following] == [ACTION_INFO]
    assert following_total == 2


async def test_a_soft_deleted_rule_is_gone_from_the_automation_list():
    """The read projection keeps the row but the list hides it. The fallback has
    to hide it too, or a stale read would resurrect a rule the user deleted."""

    repository = FakeAutomationRepository(
        [
            make_automation(AUTOMATION_A),
            make_automation(AUTOMATION_DELETED, deleted_at=datetime(2026, 2, 1)),
        ]
    )
    handler = ListFallbackAutomationsQueryHandler(repository)

    automations, total = await handler.handle(
        ListFallbackAutomationsQuery(
            user_id=7,
            page=make_page(),
            filters=FallbackAutomationFilters(),
        )
    )

    assert [str(rule.id) for rule in automations] == [AUTOMATION_A]
    assert total == 1


async def test_the_enabled_filter_is_a_tristate():
    repository = FakeAutomationRepository(
        [
            make_automation(AUTOMATION_A, enabled=True),
            make_automation(AUTOMATION_B, enabled=False),
        ]
    )
    handler = ListFallbackAutomationsQueryHandler(repository)

    async def listed(enabled: bool | None) -> list[str]:
        automations, _ = await handler.handle(
            ListFallbackAutomationsQuery(
                user_id=7,
                page=make_page(),
                filters=FallbackAutomationFilters(enabled=enabled),
            )
        )
        return sorted(str(rule.id) for rule in automations)

    assert await listed(True) == [AUTOMATION_A]
    assert await listed(False) == [AUTOMATION_B]
    assert await listed(None) == sorted([AUTOMATION_A, AUTOMATION_B])


async def test_a_single_rule_reads_back_whole():
    repository = FakeAutomationRepository([make_automation(AUTOMATION_A)])
    handler = GetFallbackAutomationQueryHandler(repository)

    automation = await handler.handle(
        GetFallbackAutomationQuery(user_id=7, automation_id=UUID(AUTOMATION_A))
    )

    assert str(automation.id) == AUTOMATION_A
    assert automation.trigger.type == "event"
    assert automation.trigger.event == "transaction.created"
    assert automation.trigger.schedule is None


async def test_the_badge_counts_the_unread_and_the_whole():
    repository = FakeNotificationRepository(
        [
            make_notification(NOTIFICATION_A),
            make_notification(NOTIFICATION_B, acknowledged_at=datetime(2026, 1, 2)),
        ]
    )
    handler = CountFallbackNotificationsQueryHandler(repository)

    counts = await handler.handle(CountFallbackNotificationsQuery(user_id=7))

    assert counts.unacknowledged == 1
    assert counts.total == 2
