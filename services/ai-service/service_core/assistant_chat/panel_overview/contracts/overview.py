from dataclasses import dataclass

from .signal import Signal


@dataclass(frozen=True, slots=True)
class Overview:
    """Both collections are small, complete and not paginated."""

    signals: tuple[Signal, ...]
    prompts: tuple[str, ...]
