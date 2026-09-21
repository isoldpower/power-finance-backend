from dataclasses import dataclass

from .signal import Signal


@dataclass(frozen=True, slots=True)
class Overview:
    signals: tuple[Signal, ...]
    prompts: tuple[str, ...]
