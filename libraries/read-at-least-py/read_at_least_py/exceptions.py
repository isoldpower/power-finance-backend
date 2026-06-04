class ReadAtLeastError(Exception):
    """Base class for read-your-writes failures."""


class NotCaughtUp(ReadAtLeastError):
    """Raised when the read side has not applied enough writes to satisfy a
    client's Read-At-Least requirement."""

    def __init__(self, scope: str, required: int, applied: int | None) -> None:
        self.scope = scope
        self.required = required
        self.applied = applied

        super().__init__(
            f"read model for scope {scope!r} is at seq {applied}, "
            f"behind required read-at-least seq {required}"
        )
