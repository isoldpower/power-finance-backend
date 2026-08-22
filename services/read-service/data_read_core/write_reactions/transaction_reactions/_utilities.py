from dataclasses import dataclass

from data_read_core.shared.postgres_orm import WalletReadModel


@dataclass(frozen=True)
class WalletLabel:
    currency_code: str
    name: str


async def _wallet_currency(wallet_id: str) -> str:
    return (await _wallet_label(wallet_id)).currency_code


async def _wallet_label(wallet_id: str) -> WalletLabel:
    requested_wallet = await (
        WalletReadModel.objects.filter(id=wallet_id).values_list("currency_code", "title").afirst()
    )
    if requested_wallet is None:
        return WalletLabel(currency_code="", name="")

    currency_code, title = requested_wallet
    return WalletLabel(
        currency_code=currency_code or "",
        name=title or "",
    )
