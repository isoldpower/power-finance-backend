from uuid import UUID

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q

from finances.application.interfaces import WalletRepository
from finances.domain.entities import Wallet, ResolvedFilterTree

from ..mappers import WalletMapper
from ..orm import WalletModel


class DjangoWalletRepository(WalletRepository):
    async def get_user_wallet_by_id(self, wallet_id: UUID, user_id: int) -> Wallet:
        requested_wallet: WalletModel = await (WalletModel.objects
            .select_related("currency")
            .aget(id=wallet_id, user_id=user_id))

        return WalletMapper.to_domain(requested_wallet)

    async def get_user_wallet_for_update(self, wallet_id: UUID, user_id: int) -> Wallet:
        requested_wallet: WalletModel = await (WalletModel.objects
            .select_for_update()
            .select_related("currency")
            .aget(id=wallet_id, user_id=user_id))

        return WalletMapper.to_domain(requested_wallet)

    async def soft_delete_wallet(self, wallet_id: UUID, user_id: int) -> Wallet:
        try:
            requested_wallet: WalletModel = await WalletModel.objects.aget(
                id=wallet_id,
                user_id=user_id,
            )
        except WalletModel.DoesNotExist:
            raise ObjectDoesNotExist("Wallet with specified ID does not exist.")

        domain_wallet = WalletMapper.to_domain(requested_wallet)
        await requested_wallet.adelete()

        return domain_wallet

    async def create_wallet(self, wallet: Wallet) -> Wallet:
        created_wallet = WalletModel()
        WalletMapper.update_model(created_wallet, wallet)
        await created_wallet.asave()

        return WalletMapper.to_domain(created_wallet)

    async def get_wallet_by_id(self, wallet_id: UUID) -> Wallet:
        requested_wallet: WalletModel = await (WalletModel.objects
            .select_related("currency")
            .aget(id=wallet_id))

        return WalletMapper.to_domain(requested_wallet)

    async def get_user_wallets(self, user_id: int) -> list[Wallet]:
        user_wallets = (WalletModel.objects
            .filter(user_id=user_id)
            .select_related("currency")
            .order_by("-created_at", "id"))

        return [WalletMapper.to_domain(wallet) async for wallet in user_wallets]

    async def get_ordered_user_wallets(self, user_id: int) -> list[Wallet]:
        user_wallets = (WalletModel.objects
            .filter(user_id=user_id)
            .select_related("currency")
            .order_by('created_at', 'id'))

        return [WalletMapper.to_domain(wallet) async for wallet in user_wallets]

    async def save_wallet(self, wallet: Wallet) -> Wallet:
        requested_wallet = await (WalletModel.objects
            .select_related("currency")
            .aget(id=wallet.id))
        modified_fields = WalletMapper.get_changed_fields(requested_wallet, wallet)

        WalletMapper.update_model(requested_wallet, wallet)

        await requested_wallet.asave(update_fields=modified_fields)
        return WalletMapper.to_domain(requested_wallet)

    async def list_wallets_with_filters(self, tree: ResolvedFilterTree, user_id: int) -> list[Wallet]:
        filtered_wallets = (WalletModel.objects
            .filter(Q(user_id=user_id) & tree.django_query)
            .select_related("currency")
            .order_by()
            .distinct())

        return [WalletMapper.to_domain(wallet) async for wallet in filtered_wallets]