from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RoutedReplies:
    """What dispatching one message produced."""

    claimed: bool
    replies: tuple[str, ...] = ()
