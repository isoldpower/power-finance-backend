from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AccountSpec:
    """An account named but not yet identified."""

    group: str
    name: str
