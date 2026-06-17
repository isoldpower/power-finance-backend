from data_read_core.shared.postgres_orm import TransactionReadModel


async def fetch_owned_transaction(
    user_id: int,
    transaction_id: str,
) -> TransactionReadModel | None:
    return await TransactionReadModel.objects.filter(
        id=transaction_id,
        user_id=user_id,
    ).afirst()
