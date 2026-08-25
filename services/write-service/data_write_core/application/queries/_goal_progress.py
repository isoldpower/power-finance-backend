from decimal import Decimal
from uuid import UUID

from data_write_core.domain.entities import GoalEntity

from ..interfaces import MoneyFlowRepository


async def load_goal_progress(
    goal: GoalEntity,
    money_flow_repository: MoneyFlowRepository,
) -> Decimal:
    goal_id = UUID(goal.unique_id)
    checkpoint = await money_flow_repository.get_checkpoint(goal_id)
    settled_at = checkpoint.created_at.isoformat() if checkpoint else None
    unsettled = await money_flow_repository.get_unsettled_flows(goal_id, settled_at)

    base = checkpoint.balance if checkpoint else Decimal("0")

    return base + sum((flow.amount for flow in unsettled), Decimal("0"))
