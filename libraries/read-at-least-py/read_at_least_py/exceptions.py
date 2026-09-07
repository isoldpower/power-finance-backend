class ReadAtLeastError(Exception):
    pass


class NotCaughtUp(ReadAtLeastError):
    def __init__(self, scope: str, required: int, applied: int | None) -> None:
        self.scope = scope
        self.required = required
        self.applied = applied

        super().__init__(
            f"read model for scope {scope!r} is at seq {applied}, "
            f"behind required read-at-least seq {required}"
        )
