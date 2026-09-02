from datetime import UTC, datetime
from uuid import UUID

from data_write_core.domain.automations import (
    TriggerEvent,
    TriggerSchedule,
    transaction_run_key,
    wallet_run_key,
)
from data_write_core.domain.entities import AutomationEntity

from ....bootstrap import LazyRegistry
from ....interfaces import (
    AutomationRepository,
    EffectExecutor,
    GoalRepository,
    MoneyContainerRepository,
    MoneyFlowRepository,
    OutboxRepository,
    TransactionRepository,
    WalletRepository,
)
from ...automations.record_run import RecordAutomationRunCommandHandler
from .rule_runner import RuleRunner
from .subject_loader import SubjectLoader


class AutomationEngine:
    def __init__(
        self,
        executors: dict[str, EffectExecutor],
        automation_repository: AutomationRepository | None = None,
        transaction_repository: TransactionRepository | None = None,
        money_flow_repository: MoneyFlowRepository | None = None,
        wallet_repository: WalletRepository | None = None,
        goal_repository: GoalRepository | None = None,
        container_repository: MoneyContainerRepository | None = None,
        outbox_repository: OutboxRepository | None = None,
    ) -> None:
        pick = LazyRegistry()
        automation_repository = pick(automation_repository, "automation_repository")
        transaction_repository = pick(transaction_repository, "transaction_repository")
        money_flow_repository = pick(money_flow_repository, "money_flow_repository")
        wallet_repository = pick(wallet_repository, "wallet_repository")
        goal_repository = pick(goal_repository, "goal_repository")
        container_repository = pick(container_repository, "money_container_repository")
        outbox_repository = pick(outbox_repository, "outbox_repository")

        self._automation_repository = automation_repository
        self._wallet_repository = wallet_repository
        self._subjects = SubjectLoader(
            transaction_repository=transaction_repository,
            money_flow_repository=money_flow_repository,
            wallet_repository=wallet_repository,
            goal_repository=goal_repository,
            container_repository=container_repository,
        )
        self._runner = RuleRunner(
            automation_repository=automation_repository,
            record_run_handler=RecordAutomationRunCommandHandler(
                automation_repository=automation_repository,
                outbox_repository=outbox_repository,
            ),
            executors=executors,
        )

    async def run_for_transaction(
        self,
        user_id: int,
        user_external_id: str,
        transaction_id: UUID,
        event: str = TriggerEvent.TRANSACTION_CREATED,
    ) -> list[str]:
        subject = await self._subjects.for_transaction(transaction_id, user_id)
        if subject is None:
            return []

        rules = await self._automation_repository.list_live_for_event(user_id, event)

        return await self._runner.run(
            rules,
            subject,
            user_id=user_id,
            user_external_id=user_external_id,
            run_key=transaction_run_key(subject.subject_id),
        )

    async def run_scheduled(
        self,
        schedule: str = TriggerSchedule.DAILY,
        passed_timestamp: datetime | None = None,
    ) -> list[str]:
        timestamp_now = passed_timestamp or datetime.now(UTC)
        applied_automations: list[str] = []

        for rule in await self._automation_repository.list_live_scheduled(schedule):
            applied_automations.extend(
                await self._run_scheduled_rule(rule, schedule, timestamp_now)
            )

        return applied_automations

    async def _run_scheduled_rule(
        self,
        rule: AutomationEntity,
        schedule: str,
        moment: datetime,
    ) -> list[str]:
        user_id = int(rule.user_id)
        applied_automations: list[str] = []

        for wallet in await self._wallet_repository.get_user_wallets(user_id):
            if wallet.deleted_at is not None:
                continue

            subject = await self._subjects.for_wallet(wallet, user_id)
            applied_automations.extend(
                await self._runner.run(
                    [rule],
                    subject,
                    user_id=user_id,
                    user_external_id=rule.user_external_id,
                    run_key=wallet_run_key(
                        wallet.unique_id,
                        schedule,
                        moment,
                    ),
                )
            )

        return applied_automations
