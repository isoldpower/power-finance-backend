from uuid import UUID

from data_write_core.application.interfaces import WalletRepository
from data_write_core.domain.entities import WalletEntity

from ..orm import WalletModel
from .mappers import WalletMapper


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
        # with_deleted() so a SAGA-compensation `restore` can find
        # rows that the soft-delete manager would otherwise hide.
        requested_wallet = await (
            WalletModel.objects.with_deleted().select_related("currency").aget(id=wallet.unique_id)
        )
        WalletMapper.apply_to_model(requested_wallet, wallet)
        await requested_wallet.asave()
        return WalletMapper.to_domain(requested_wallet)

    async def hard_delete_wallet(self, wallet_id: UUID) -> None:
        # Bulk delete bypasses the model's soft-delete override and
        # the manager's deleted_at filter, so this works whether the
        # row is soft-deleted or live. Idempotent.
        await WalletModel.objects.with_deleted().filter(id=wallet_id).adelete()
