from uuid import UUID

from finances.application.interfaces import WalletSelectorsCollection
from finances.domain.entities import Wallet

from ..mappers import WalletMapper
from ..orm import WalletModel


class DjangoWalletSelectorsCollection(WalletSelectorsCollection):
    async def get_ordered_user_wallets(self, user_id: int) -> list[Wallet]:
        requested_wallets = (WalletModel.objects
            .filter(user_id=user_id)
            .order_by('created_at', 'id'))

        return [WalletMapper.to_domain(wallet) async for wallet in requested_wallets]

    async def get_single_wallet(self, user_id: int, wallet_id: UUID) -> Wallet:
        requested_wallet = await WalletModel.objects.aget(user_id=user_id, id=wallet_id)

        return WalletMapper.to_domain(requested_wallet)
