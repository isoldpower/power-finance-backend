from collections.abc import Sequence

from ..contracts import DispatchedPostings, PostingLeg, TransactionFacts
from ..repositories import AccountRepository
from .template_account import TemplateAccount


class TemplateDispatcher:
    """Emits one leg per template account, against the user's own copies."""

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
        transaction_amount = abs(transaction.amount)
        transaction_title = transaction.name or "Transaction"

        return DispatchedPostings(
            legs=tuple(
                PostingLeg(
                    account_id=account_id,
                    title=transaction_title,
                    debit=account.debit,
                    amount=transaction_amount,
                    position=position,
                    currency_code=transaction.currency_code or None,
                )
                for position, (account, account_id) in enumerate(
                    zip(self._template, account_ids, strict=True)
                )
            ),
            balanced=True,
            comment="",
            backend="template",
        )
