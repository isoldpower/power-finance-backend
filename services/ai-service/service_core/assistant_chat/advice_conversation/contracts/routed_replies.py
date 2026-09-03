from collections.abc import AsyncIterator
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RoutedReplies:
    claimed: bool
    frames: AsyncIterator[dict]
