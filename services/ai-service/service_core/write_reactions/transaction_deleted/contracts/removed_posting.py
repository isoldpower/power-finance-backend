from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class RemovedPosting:
    """A leg that a deletion walked away from."""

    posting_id: UUID
    account_id: UUID
