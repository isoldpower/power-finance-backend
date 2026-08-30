from dataclasses import dataclass

from ..contracts import AccountSpec


@dataclass(frozen=True, slots=True)
class TemplateAccount:
    """One placeholder account and the side it always takes."""

    specification: AccountSpec
    debit: bool
