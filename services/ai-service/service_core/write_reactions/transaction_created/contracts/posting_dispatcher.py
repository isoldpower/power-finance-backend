from typing import Protocol, runtime_checkable

from .dispatched_postings import DispatchedPostings
from .transaction_facts import TransactionFacts


@runtime_checkable
class PostingDispatcher(Protocol):
    async def dispatch(
        self,
        transaction: TransactionFacts,
    ) -> DispatchedPostings: ...
