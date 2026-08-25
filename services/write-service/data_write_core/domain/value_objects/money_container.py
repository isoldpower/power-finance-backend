from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class MoneyContainerKind(StrEnum):
    WALLET = "wallet"
    GOAL = "goal"


@dataclass(frozen=True)
class MoneyContainerRef:
    id: UUID
    kind: MoneyContainerKind
    currency_code: str
    title: str
    is_closed: bool = False

    @property
    def is_wallet(self) -> bool:
        return self.kind is MoneyContainerKind.WALLET

    @property
    def is_goal(self) -> bool:
        return self.kind is MoneyContainerKind.GOAL
