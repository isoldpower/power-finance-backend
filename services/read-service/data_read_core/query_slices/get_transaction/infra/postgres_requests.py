from data_read_core.shared.postgres_orm import (
    AccountDispatchReadModel,
    AccountPostingReadModel,
    TransactionReadModel,
)


async def fetch_owned_transaction(
    user_id: int,
    transaction_id: str,
) -> TransactionReadModel | None:
    return await TransactionReadModel.objects.filter(
        id=transaction_id,
        user_id=user_id,
    ).afirst()


async def fetch_transaction_postings(
    transaction_id: str,
) -> list[AccountPostingReadModel]:
    return [
        posting
        async for posting in AccountPostingReadModel.objects.filter(
            transaction_id=transaction_id,
        ).order_by("position", "id")
    ]


async def fetch_transaction_dispatch(
    transaction_id: str,
) -> AccountDispatchReadModel | None:
    return await AccountDispatchReadModel.objects.filter(
        transaction_id=transaction_id,
    ).afirst()
