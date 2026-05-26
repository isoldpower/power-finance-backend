import logging
from collections.abc import Callable

from ..message import ConsumedMessage
from .store import DedupeStore

logger = logging.getLogger(__name__)


EventIdExtractor = Callable[[ConsumedMessage], str | None]


class DedupeGate:
    def __init__(
        self,
        dedupe_store: DedupeStore | None,
        event_id_extractor: EventIdExtractor | None,
    ) -> None:
        self._dedupe_store = dedupe_store
        self._event_id_extractor = event_id_extractor

    async def already_processed(self, message: ConsumedMessage) -> bool:
        if self._dedupe_store is None or self._event_id_extractor is None:
            return False

        event_id = self._event_id_extractor(message)
        if event_id is None:
            return False

        if await self._dedupe_store.seen(event_id):
            logger.debug("kafka.dedupe.skip", extra={"event_id": event_id})
            return True
        return False
