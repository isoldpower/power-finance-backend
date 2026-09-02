"""What turns one outbox event into a run of the user's rules.

Split on the two halves of a trigger name. The SUBJECT — `transaction` — decides
which handler serves the event, what its payload looks like and how the subject
is loaded. The OCCURRENCE — `.created` / `.updated` — decides only which stored
rules are asked, because a rule declares the occurrence it wants.
"""

import json
from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any
from uuid import UUID

from kafka_client_py import PoisonError
from kafka_consumer_py import EventMessage


class EventAutomationHandler(ABC):
    # Which outbox events this handler serves, and the trigger each one means to
    # a rule. Two events can map to one trigger: the user wrote "when a
    # transaction changes", not "when a column changes".
    triggers: Mapping[str, str]
    subject: str
    subject_key: str

    def serves(self, event_type: str) -> bool:
        return event_type in self.triggers

    async def handle(self, event: EventMessage) -> list[str]:
        payload = self.decode(event.payload)

        return await self.run(
            trigger=self.triggers[event.event_type],
            subject_id=self.subject_id(payload),
            user_id=self.user_id(payload),
            # The Kafka key IS the user's external id — the partition key every
            # outbox entry is written with — so no event carries it twice.
            user_external_id=event.partition_key,
        )

    def decode(self, payload: bytes) -> dict[str, Any]:
        try:
            return dict(json.loads(payload))
        except (ValueError, TypeError) as broken:
            raise PoisonError(
                f"{self.subject} event with an unreadable payload: {broken}"
            ) from broken

    def subject_id(self, payload: dict[str, Any]) -> UUID:
        return self._required(payload, self.subject_key, UUID)

    def user_id(self, payload: dict[str, Any]) -> int:
        return self._required(payload, "user_id", int)

    @abstractmethod
    async def run(
        self,
        *,
        trigger: str,
        subject_id: UUID,
        user_id: int,
        user_external_id: str,
    ) -> list[str]:
        raise NotImplementedError()

    def _required(self, payload: dict[str, Any], key: str, read: Any) -> Any:
        try:
            return read(str(payload[key]))
        except (ValueError, KeyError, TypeError) as broken:
            raise PoisonError(
                f"{self.subject} event without a usable `{key}`: {broken}",
            ) from broken
