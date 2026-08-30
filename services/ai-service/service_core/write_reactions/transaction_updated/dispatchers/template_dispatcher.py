from collections.abc import Sequence

from ..contracts import DispatchedPostings, PostingLeg, TransactionFacts
from ..repositories import AccountRepository
from .template_account import TemplateAccount


class TemplateDispatcher:
    def __init__(
        self,
        accounts: AccountRepository,
        template: Sequence[TemplateAccount],
    ) -> None:
        self._accounts = accounts
        self._template = tuple(template)

    async def dispatch(self, transaction: TransactionFacts) -> DispatchedPostings:
        account_ids = await self._accounts.resolve(
            transaction.user_id,
            [account.specification for account in self._template],
        )
        amount = abs(transaction.amount)
        title = transaction.name or "Transaction"

        return DispatchedPostings(
            legs=tuple(
                PostingLeg(
                    account_id=account_id,
                    title=title,
                    debit=account.debit,
                    amount=amount,
                    position=position,
                )
                for position, (account, account_id) in enumerate(
                    zip(self._template, account_ids, strict=True)
                )
            ),
            balanced=True,
            comment="",
            backend="template",
        )
