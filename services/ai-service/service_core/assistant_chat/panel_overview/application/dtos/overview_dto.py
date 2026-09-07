from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SignalDTO:
    label: str
    value: str
    tone: str


@dataclass(frozen=True, slots=True)
class OverviewDTO:
    signals: tuple[SignalDTO, ...]
    prompts: tuple[str, ...]
