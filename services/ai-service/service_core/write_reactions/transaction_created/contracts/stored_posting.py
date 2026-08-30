from dataclasses import dataclass
from uuid import UUID

from .posting_leg import PostingLeg


@dataclass(frozen=True, slots=True)
class StoredPosting:
    """A leg once it has an identity of its own."""

    posting_id: UUID
    leg: PostingLeg
