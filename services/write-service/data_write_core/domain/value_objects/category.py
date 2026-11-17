from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID, uuid5


class CategoryKind(StrEnum):
    TRANSACTION = "transaction"
    WALLET = "wallet"


@dataclass(frozen=True)
class CategoryReference:
    id: UUID
    name: str
    is_global: bool


GLOBAL_CATEGORY_NAMESPACE = UUID("7d3f0f0e-2c1b-4c55-9a43-6f1b9c2e8a10")


def global_category_id(kind: CategoryKind, name: str) -> UUID:
    return uuid5(GLOBAL_CATEGORY_NAMESPACE, f"{kind}:{name.casefold()}")
