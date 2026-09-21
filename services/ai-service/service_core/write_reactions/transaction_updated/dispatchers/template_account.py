from dataclasses import dataclass

from ..contracts import AccountSpec


@dataclass(frozen=True, slots=True)
class TemplateAccount:
    specification: AccountSpec
    debit: bool
