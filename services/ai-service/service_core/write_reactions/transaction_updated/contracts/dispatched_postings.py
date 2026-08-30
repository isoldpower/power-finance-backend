from dataclasses import dataclass

from .posting_leg import PostingLeg


@dataclass(frozen=True, slots=True)
class DispatchedPostings:
    """A dispatcher's whole answer for one transaction."""

    legs: tuple[PostingLeg, ...]
    balanced: bool
    comment: str
    backend: str
