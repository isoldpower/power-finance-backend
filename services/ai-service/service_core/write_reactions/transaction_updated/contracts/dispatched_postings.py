from dataclasses import dataclass

from .posting_leg import PostingLeg


@dataclass(frozen=True, slots=True)
class DispatchedPostings:
    legs: tuple[PostingLeg, ...]
    balanced: bool
    comment: str
    backend: str
