from data_read_core.shared.postgres_orm import WalletReadModel


async def _wallet_currency(wallet_id: str) -> str:
    currency_code = await (
        WalletReadModel.objects.filter(id=wallet_id)
        .values_list("currency_code", flat=True)
        .afirst()
    )

    return currency_code or ""
