from .exceptions import NotCaughtUp
from .sequence_reader import AppliedSeqReader


class ReadAtLeastGate:
    """Decides whether the read side has applied enough writes to satisfy a
    client's Read-At-Least requirement."""

    def __init__(self, reader: AppliedSeqReader) -> None:
        self._reader = reader

    async def ensure_caught_up(self, scope: str, required: int | None) -> None:
        """Raise ``NotCaughtUp`` unless the read side has applied at least
        ``required`` for ``scope``."""

        if required is None:
            return

        applied = await self._reader.applied_seq(scope)
        if applied is None or applied < required:
            raise NotCaughtUp(scope=scope, required=required, applied=applied)
