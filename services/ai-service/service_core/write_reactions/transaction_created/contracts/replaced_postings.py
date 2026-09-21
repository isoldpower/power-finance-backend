from dataclasses import dataclass

from .removed_posting import RemovedPosting
from .stored_posting import StoredPosting


@dataclass(frozen=True, slots=True)
class ReplacedPostings:
    removed: tuple[RemovedPosting, ...]
    created: tuple[StoredPosting, ...]
