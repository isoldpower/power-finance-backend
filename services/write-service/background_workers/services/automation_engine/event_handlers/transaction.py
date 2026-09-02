from uuid import UUID

from data_write_core.application.commands.automations.engine import (
    EFFECT_EXECUTORS,
    AutomationEngine,
)
from data_write_core.domain.automations import SubjectType, TriggerEvent

from .base import EventAutomationHandler


class TransactionAutomationHandler(EventAutomationHandler):
    subject = SubjectType.TRANSACTION
    subject_key = "transaction_id"
    triggers = {
        "TransactionCreated": TriggerEvent.TRANSACTION_CREATED,
        "TransactionUpdated": TriggerEvent.TRANSACTION_UPDATED,
        # An amount edit and a metadata edit are one trigger to a rule.
        "TransactionMetadataUpdated": TriggerEvent.TRANSACTION_UPDATED,
    }

    async def run(
        self,
        *,
        trigger: str,
        subject_id: UUID,
        user_id: int,
        user_external_id: str,
    ) -> list[str]:
        return await AutomationEngine(EFFECT_EXECUTORS).run_for_transaction(
            user_id=user_id,
            user_external_id=user_external_id,
            transaction_id=subject_id,
            event=trigger,
        )
