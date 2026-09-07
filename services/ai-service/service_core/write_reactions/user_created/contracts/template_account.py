from dataclasses import dataclass

from .account_spec import AccountSpec


@dataclass(frozen=True, slots=True)
class TemplateAccount:
    specification: AccountSpec
    debit: bool
