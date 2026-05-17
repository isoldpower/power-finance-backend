from uuid import UUID

from data_write_core.application.interfaces import WalletRepository
from data_write_core.domain.entities import WalletEntity

from ..mappers import WalletMapper
from ..orm import WalletModel


class DjangoWalletRepository(WalletRepository):
    async def get_user_wallet_by_id(self, wallet_id: UUID, user_id: int) -> WalletEntity:
        requested_wallet: WalletModel = await WalletModel.objects.select_related("currency").aget(
            id=wallet_id, user_id=user_id
        )

        return WalletMapper.to_domain(requested_wallet)

    async def get_user_wallet_for_update(self, wallet_id: UUID, user_id: int) -> WalletEntity:
        requested_wallet: WalletModel = await (
            WalletModel.objects.select_for_update()
            .select_related("currency")
            .aget(id=wallet_id, user_id=user_id)
        )

        return WalletMapper.to_domain(requested_wallet)

    async def create_wallet(self, wallet: WalletEntity) -> WalletEntity:
        created_wallet = WalletModel()
        WalletMapper.apply_to_model(created_wallet, wallet)
        await created_wallet.asave()

        refreshed = await WalletModel.objects.select_related("currency").aget(id=created_wallet.id)
        return WalletMapper.to_domain(refreshed)

    async def get_wallet_by_id(self, wallet_id: UUID) -> WalletEntity:
        requested_wallet: WalletModel = await WalletModel.objects.select_related("currency").aget(
            id=wallet_id
        )

        return WalletMapper.to_domain(requested_wallet)

    async def save_wallet(self, wallet: WalletEntity) -> WalletEntity:
        requested_wallet = await WalletModel.objects.select_related("currency").aget(
            id=wallet.unique_id
        )
        WalletMapper.apply_to_model(requested_wallet, wallet)
        await requested_wallet.asave()
        return WalletMapper.to_domain(requested_wallet)
