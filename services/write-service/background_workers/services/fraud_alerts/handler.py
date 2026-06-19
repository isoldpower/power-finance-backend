import logging

from kafka_client_py import ConsumedMessage, PoisonError

from background_workers.services.fraud_alerts.store import (
    SuspendedUser,
    SuspendedUserStore,
)

logger = logging.getLogger("background_workers.fraud_alerts")


def _parse_fraud_alert(message: ConsumedMessage) -> SuspendedUser:
    if message.key is None:
        raise PoisonError("Fraud alert missing key (clerk id)")

    clerk_id = message.key.decode("utf-8")
    if not clerk_id:
        raise PoisonError("Fraud alert has an empty clerk id")

    reason = message.value.decode("utf-8") if message.value is not None else ""
    return SuspendedUser(clerk_id=clerk_id, reason=reason)


class FraudAlertHandler:
    """Suspends the user named by each fraud alert in the suspended-user store."""

    def __init__(self, store: SuspendedUserStore) -> None:
        self._store = store

    async def handle(self, message: ConsumedMessage) -> None:
        user = _parse_fraud_alert(message)
        await self._store.suspend(user)
        logger.info("fraud_alerts: suspended user clerk_id=%s", user.clerk_id)
