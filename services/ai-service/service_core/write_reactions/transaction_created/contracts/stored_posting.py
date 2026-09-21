from dataclasses import dataclass
from uuid import UUID

from .posting_leg import PostingLeg


@dataclass(frozen=True, slots=True)
class StoredPosting:
    posting_id: UUID
    leg: PostingLeg
