from collections.abc import Sequence

from ..contracts import AccountSpec


class UnknownAccountsError(Exception):
    def __init__(self, user_id: int, missing: Sequence[AccountSpec]) -> None:
        named = ", ".join(f"{spec.group}/{spec.name}" for spec in missing)
        super().__init__(f"user {user_id} has no account for: {named}")

        self.user_id = user_id
        self.missing = tuple(missing)
