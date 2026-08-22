from uuid import UUID

from write_service.common.pagination import (
    FAVORITE_CREATED_AT_DESC,
    PageRequest,
    apply_keyset,
)

from data_write_core.application.interfaces import WalletRepository
from data_write_core.domain.entities import WalletEntity

from ..orm import WalletModel
from .mappers import WalletMapper


class DjangoWalletRepository(WalletRepository):
    async def get_user_wallet_by_id(self, wallet_id: UUID, user_id: int) -> WalletEntity:
        requested_wallet: WalletModel = await (
            WalletModel.objects.with_deleted()
            .select_related("currency")
            .aget(id=wallet_id, user_id=user_id)
        )

        return WalletMapper.to_domain(requested_wallet)

    async def get_user_wallets(
        self,
        user_id: int,
        page: PageRequest | None = None,
    ) -> list[WalletEntity]:
        queryset = WalletModel.objects.select_related("currency").filter(user_id=user_id)
        rows = (
            apply_keyset(queryset, page)
            if page
            else queryset.order_by(*FAVORITE_CREATED_AT_DESC.django_ordering)
        )

        return [WalletMapper.to_domain(wallet) async for wallet in rows]

    async def count_user_wallets(self, user_id: int) -> int:
        return await WalletModel.objects.filter(user_id=user_id).acount()

    async def get_user_wallet_for_update(self, wallet_id: UUID, user_id: int) -> WalletEntity:
        requested_wallet: WalletModel = await (
            WalletModel.objects.with_deleted()
            .select_for_update()
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
        requested_wallet = await (
            WalletModel.objects.with_deleted().select_related("currency").aget(id=wallet.unique_id)
        )
        WalletMapper.apply_to_model(requested_wallet, wallet)
        await requested_wallet.asave()
        return WalletMapper.to_domain(requested_wallet)

    async def hard_delete_wallet(self, wallet_id: UUID) -> None:
        await WalletModel.objects.with_deleted().filter(id=wallet_id).adelete()
